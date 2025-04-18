"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.BrowsingContextProcessor = void 0;
const protocol_js_1 = require("../../../protocol/protocol.js");
class BrowsingContextProcessor {
    #browserCdpClient;
    #browsingContextStorage;
    #eventManager;
    constructor(browserCdpClient, browsingContextStorage, eventManager) {
        this.#browserCdpClient = browserCdpClient;
        this.#browsingContextStorage = browsingContextStorage;
        this.#eventManager = eventManager;
        this.#eventManager.addSubscribeHook(protocol_js_1.ChromiumBidi.BrowsingContext.EventNames.ContextCreated, this.#onContextCreatedSubscribeHook.bind(this));
    }
    getTree(params) {
        const resultContexts = params.root === undefined
            ? this.#browsingContextStorage.getTopLevelContexts()
            : [this.#browsingContextStorage.getContext(params.root)];
        return {
            contexts: resultContexts.map((c) => c.serializeToBidiValue(params.maxDepth ?? Number.MAX_VALUE)),
        };
    }
    async create(params) {
        let referenceContext;
        let userContext = 'default';
        if (params.referenceContext !== undefined) {
            referenceContext = this.#browsingContextStorage.getContext(params.referenceContext);
            if (!referenceContext.isTopLevelContext()) {
                throw new protocol_js_1.InvalidArgumentException(`referenceContext should be a top-level context`);
            }
            userContext = referenceContext.userContext;
        }
        if (params.userContext !== undefined) {
            userContext = params.userContext;
        }
        const existingContexts = this.#browsingContextStorage
            .getAllContexts()
            .filter((context) => context.userContext === userContext);
        let newWindow = false;
        switch (params.type) {
            case "tab" /* BrowsingContext.CreateType.Tab */:
                newWindow = false;
                break;
            case "window" /* BrowsingContext.CreateType.Window */:
                newWindow = true;
                break;
        }
        if (!existingContexts.length) {
            // If there are no contexts in the given user context, we need to set
            // newWindow to true as newWindow=false will be rejected.
            newWindow = true;
        }
        let result;
        try {
            result = await this.#browserCdpClient.sendCommand('Target.createTarget', {
                url: 'about:blank',
                newWindow,
                browserContextId: userContext === 'default' ? undefined : userContext,
                background: params.background === true,
            });
        }
        catch (err) {
            if (
            // See https://source.chromium.org/chromium/chromium/src/+/main:chrome/browser/devtools/protocol/target_handler.cc;l=90;drc=e80392ac11e48a691f4309964cab83a3a59e01c8
            err.message.startsWith('Failed to find browser context with id') ||
                // See https://source.chromium.org/chromium/chromium/src/+/main:headless/lib/browser/protocol/target_handler.cc;l=49;drc=e80392ac11e48a691f4309964cab83a3a59e01c8
                err.message === 'browserContextId') {
                throw new protocol_js_1.NoSuchUserContextException(`The context ${userContext} was not found`);
            }
            throw err;
        }
        // Wait for the new target to be attached and to be added to the browsing context
        // storage.
        const context = await this.#browsingContextStorage.waitForContext(result.targetId);
        // Wait for the new tab to be loaded to avoid race conditions in the
        // `browsingContext` events, when the `browsingContext.domContentLoaded` and
        // `browsingContext.load` events from the initial `about:blank` navigation
        // are emitted after the next navigation is started.
        // Details: https://github.com/web-platform-tests/wpt/issues/35846
        await context.lifecycleLoaded();
        return { context: context.id };
    }
    navigate(params) {
        const context = this.#browsingContextStorage.getContext(params.context);
        return context.navigate(params.url, params.wait ?? "none" /* BrowsingContext.ReadinessState.None */);
    }
    reload(params) {
        const context = this.#browsingContextStorage.getContext(params.context);
        return context.reload(params.ignoreCache ?? false, params.wait ?? "none" /* BrowsingContext.ReadinessState.None */);
    }
    async activate(params) {
        const context = this.#browsingContextStorage.getContext(params.context);
        if (!context.isTopLevelContext()) {
            throw new protocol_js_1.InvalidArgumentException('Activation is only supported on the top-level context');
        }
        await context.activate();
        return {};
    }
    async captureScreenshot(params) {
        const context = this.#browsingContextStorage.getContext(params.context);
        return await context.captureScreenshot(params);
    }
    async print(params) {
        const context = this.#browsingContextStorage.getContext(params.context);
        return await context.print(params);
    }
    async setViewport(params) {
        const context = this.#browsingContextStorage.getContext(params.context);
        if (!context.isTopLevelContext()) {
            throw new protocol_js_1.InvalidArgumentException('Emulating viewport is only supported on the top-level context');
        }
        await context.setViewport(params.viewport, params.devicePixelRatio);
        return {};
    }
    async traverseHistory(params) {
        const context = this.#browsingContextStorage.getContext(params.context);
        if (!context) {
            throw new protocol_js_1.InvalidArgumentException(`No browsing context with id ${params.context}`);
        }
        if (!context.isTopLevelContext()) {
            throw new protocol_js_1.InvalidArgumentException('Traversing history is only supported on the top-level context');
        }
        await context.traverseHistory(params.delta);
        return {};
    }
    async handleUserPrompt(params) {
        const context = this.#browsingContextStorage.getContext(params.context);
        try {
            await context.handleUserPrompt(params.accept, params.userText);
        }
        catch (error) {
            // Heuristically determine the error
            // https://source.chromium.org/chromium/chromium/src/+/main:content/browser/devtools/protocol/page_handler.cc;l=1085?q=%22No%20dialog%20is%20showing%22&ss=chromium
            if (error.message?.includes('No dialog is showing')) {
                throw new protocol_js_1.NoSuchAlertException('No dialog is showing');
            }
            throw error;
        }
        return {};
    }
    async close(params) {
        const context = this.#browsingContextStorage.getContext(params.context);
        if (!context.isTopLevelContext()) {
            throw new protocol_js_1.InvalidArgumentException(`Non top-level browsing context ${context.id} cannot be closed.`);
        }
        // Parent session of a page target session can be a `browser` or a `tab` session.
        const parentCdpClient = context.cdpTarget.parentCdpClient;
        try {
            const detachedFromTargetPromise = new Promise((resolve) => {
                const onContextDestroyed = (event) => {
                    if (event.targetId === params.context) {
                        parentCdpClient.off('Target.detachedFromTarget', onContextDestroyed);
                        resolve();
                    }
                };
                parentCdpClient.on('Target.detachedFromTarget', onContextDestroyed);
            });
            try {
                if (params.promptUnload) {
                    await context.close();
                }
                else {
                    await parentCdpClient.sendCommand('Target.closeTarget', {
                        targetId: params.context,
                    });
                }
            }
            catch (error) {
                // Swallow error that arise from the session being destroyed. Rely on the
                // `detachedFromTargetPromise` event to be resolved.
                if (!parentCdpClient.isCloseError(error)) {
                    throw error;
                }
            }
            // Sometimes CDP command finishes before `detachedFromTarget` event,
            // sometimes after. Wait for the CDP command to be finished, and then wait
            // for `detachedFromTarget` if it hasn't emitted.
            await detachedFromTargetPromise;
        }
        catch (error) {
            // Swallow error that arise from the page being destroyed
            // Example is navigating to faulty SSL certificate
            if (!(error.code === -32000 /* CdpErrorConstants.GENERIC_ERROR */ &&
                error.message === 'Not attached to an active page')) {
                throw error;
            }
        }
        return {};
    }
    async locateNodes(params) {
        const context = this.#browsingContextStorage.getContext(params.context);
        return await context.locateNodes(params);
    }
    #onContextCreatedSubscribeHook(contextId) {
        const context = this.#browsingContextStorage.getContext(contextId);
        const contextsToReport = [
            context,
            ...this.#browsingContextStorage.getContext(contextId).allChildren,
        ];
        contextsToReport.forEach((context) => {
            this.#eventManager.registerEvent({
                type: 'event',
                method: protocol_js_1.ChromiumBidi.BrowsingContext.EventNames.ContextCreated,
                params: context.serializeToBidiValue(),
            }, context.id);
        });
        return Promise.resolve();
    }
}
exports.BrowsingContextProcessor = BrowsingContextProcessor;
//# sourceMappingURL=BrowsingContextProcessor.js.map