"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CdpTarget = void 0;
const chromium_bidi_js_1 = require("../../../protocol/chromium-bidi.js");
const Deferred_js_1 = require("../../../utils/Deferred.js");
const EventEmitter_js_1 = require("../../../utils/EventEmitter.js");
const log_js_1 = require("../../../utils/log.js");
const BrowsingContextImpl_js_1 = require("../context/BrowsingContextImpl.js");
const LogManager_js_1 = require("../log/LogManager.js");
class CdpTarget extends EventEmitter_js_1.EventEmitter {
    #id;
    #cdpClient;
    #browserCdpClient;
    #parentCdpClient;
    #realmStorage;
    #eventManager;
    #preloadScriptStorage;
    #browsingContextStorage;
    #prerenderingDisabled;
    #networkStorage;
    #unblocked = new Deferred_js_1.Deferred();
    #unhandledPromptBehavior;
    #logger;
    #deviceAccessEnabled = false;
    #cacheDisableState = false;
    #fetchDomainStages = {
        request: false,
        response: false,
        auth: false,
    };
    static create(targetId, cdpClient, browserCdpClient, parentCdpClient, realmStorage, eventManager, preloadScriptStorage, browsingContextStorage, networkStorage, prerenderingDisabled, unhandledPromptBehavior, logger) {
        const cdpTarget = new CdpTarget(targetId, cdpClient, browserCdpClient, parentCdpClient, eventManager, realmStorage, preloadScriptStorage, browsingContextStorage, networkStorage, prerenderingDisabled, unhandledPromptBehavior, logger);
        LogManager_js_1.LogManager.create(cdpTarget, realmStorage, eventManager, logger);
        cdpTarget.#setEventListeners();
        // No need to await.
        // Deferred will be resolved when the target is unblocked.
        void cdpTarget.#unblock();
        return cdpTarget;
    }
    constructor(targetId, cdpClient, browserCdpClient, parentCdpClient, eventManager, realmStorage, preloadScriptStorage, browsingContextStorage, networkStorage, prerenderingDisabled, unhandledPromptBehavior, logger) {
        super();
        this.#id = targetId;
        this.#cdpClient = cdpClient;
        this.#browserCdpClient = browserCdpClient;
        this.#parentCdpClient = parentCdpClient;
        this.#eventManager = eventManager;
        this.#realmStorage = realmStorage;
        this.#preloadScriptStorage = preloadScriptStorage;
        this.#networkStorage = networkStorage;
        this.#browsingContextStorage = browsingContextStorage;
        this.#prerenderingDisabled = prerenderingDisabled;
        this.#unhandledPromptBehavior = unhandledPromptBehavior;
        this.#logger = logger;
    }
    /** Returns a deferred that resolves when the target is unblocked. */
    get unblocked() {
        return this.#unblocked;
    }
    get id() {
        return this.#id;
    }
    get cdpClient() {
        return this.#cdpClient;
    }
    get parentCdpClient() {
        return this.#parentCdpClient;
    }
    get browserCdpClient() {
        return this.#browserCdpClient;
    }
    /** Needed for CDP escape path. */
    get cdpSessionId() {
        // SAFETY we got the client by it's id for creating
        return this.#cdpClient.sessionId;
    }
    /**
     * Enables all the required CDP domains and unblocks the target.
     */
    async #unblock() {
        try {
            await Promise.all([
                this.#cdpClient.sendCommand('Page.enable'),
                // There can be some existing frames in the target, if reconnecting to an
                // existing browser instance, e.g. via Puppeteer. Need to restore the browsing
                // contexts for the frames to correctly handle further events, like
                // `Runtime.executionContextCreated`.
                // It's important to schedule this task together with enabling domains commands to
                // prepare the tree before the events (e.g. Runtime.executionContextCreated) start
                // coming.
                // https://github.com/GoogleChromeLabs/chromium-bidi/issues/2282
                this.#cdpClient
                    .sendCommand('Page.getFrameTree')
                    .then((frameTree) => this.#restoreFrameTreeState(frameTree.frameTree)),
                this.#cdpClient.sendCommand('Runtime.enable'),
                this.#cdpClient.sendCommand('Page.setLifecycleEventsEnabled', {
                    enabled: true,
                }),
                this.#cdpClient
                    .sendCommand('Page.setPrerenderingAllowed', {
                    isAllowed: !this.#prerenderingDisabled,
                })
                    .catch(() => {
                    // Ignore CDP errors, as the command is not supported by iframe targets or
                    // prerendered pages. Generic catch, as the error can vary between CdpClient
                    // implementations: Tab vs Puppeteer.
                }),
                // Enabling CDP Network domain is required for navigation detection:
                // https://github.com/GoogleChromeLabs/chromium-bidi/issues/2856.
                this.#cdpClient
                    .sendCommand('Network.enable')
                    .then(() => this.toggleNetworkIfNeeded()),
                this.#cdpClient.sendCommand('Target.setAutoAttach', {
                    autoAttach: true,
                    waitForDebuggerOnStart: true,
                    flatten: true,
                }),
                this.#initAndEvaluatePreloadScripts(),
                this.#cdpClient.sendCommand('Runtime.runIfWaitingForDebugger'),
                // Resume tab execution as well if it was paused by the debugger.
                this.#parentCdpClient.sendCommand('Runtime.runIfWaitingForDebugger'),
                this.toggleDeviceAccessIfNeeded(),
            ]);
        }
        catch (error) {
            this.#logger?.(log_js_1.LogType.debugError, 'Failed to unblock target', error);
            // The target might have been closed before the initialization finished.
            if (!this.#cdpClient.isCloseError(error)) {
                this.#unblocked.resolve({
                    kind: 'error',
                    error,
                });
                return;
            }
        }
        this.#unblocked.resolve({
            kind: 'success',
            value: undefined,
        });
    }
    #restoreFrameTreeState(frameTree) {
        const frame = frameTree.frame;
        const maybeContext = this.#browsingContextStorage.findContext(frame.id);
        if (maybeContext !== undefined) {
            // Restoring parent of already known browsing context. This means the target is
            // OOPiF and the BiDi session was connected to already existing browser instance.
            if (maybeContext.parentId === null &&
                frame.parentId !== null &&
                frame.parentId !== undefined) {
                maybeContext.parentId = frame.parentId;
            }
        }
        if (maybeContext === undefined && frame.parentId !== undefined) {
            // Restore not yet known nested frames. The top-level frame is created when the
            // target is attached.
            const parentBrowsingContext = this.#browsingContextStorage.getContext(frame.parentId);
            BrowsingContextImpl_js_1.BrowsingContextImpl.create(frame.id, frame.parentId, parentBrowsingContext.userContext, parentBrowsingContext.cdpTarget, this.#eventManager, this.#browsingContextStorage, this.#realmStorage, frame.url, undefined, this.#unhandledPromptBehavior, this.#logger);
        }
        frameTree.childFrames?.map((frameTree) => this.#restoreFrameTreeState(frameTree));
    }
    async toggleFetchIfNeeded() {
        const stages = this.#networkStorage.getInterceptionStages(this.topLevelId);
        if (this.#fetchDomainStages.request === stages.request &&
            this.#fetchDomainStages.response === stages.response &&
            this.#fetchDomainStages.auth === stages.auth) {
            return;
        }
        const patterns = [];
        this.#fetchDomainStages = stages;
        if (stages.request || stages.auth) {
            // CDP quirk we need request interception when we intercept auth
            patterns.push({
                urlPattern: '*',
                requestStage: 'Request',
            });
        }
        if (stages.response) {
            patterns.push({
                urlPattern: '*',
                requestStage: 'Response',
            });
        }
        if (patterns.length) {
            await this.#cdpClient.sendCommand('Fetch.enable', {
                patterns,
                handleAuthRequests: stages.auth,
            });
        }
        else {
            const blockedRequest = this.#networkStorage
                .getRequestsByTarget(this)
                .filter((request) => request.interceptPhase);
            void Promise.allSettled(blockedRequest.map((request) => request.waitNextPhase))
                .then(async () => {
                const blockedRequest = this.#networkStorage
                    .getRequestsByTarget(this)
                    .filter((request) => request.interceptPhase);
                if (blockedRequest.length) {
                    return await this.toggleFetchIfNeeded();
                }
                return await this.#cdpClient.sendCommand('Fetch.disable');
            })
                .catch((error) => {
                this.#logger?.(log_js_1.LogType.bidi, 'Disable failed', error);
            });
        }
    }
    /**
     * Toggles CDP "Fetch" domain and enable/disable network cache.
     */
    async toggleNetworkIfNeeded() {
        // Although the Network domain remains active, Fetch domain activation and caching
        // settings should be managed dynamically.
        try {
            await Promise.all([
                this.toggleSetCacheDisabled(),
                this.toggleFetchIfNeeded(),
            ]);
        }
        catch (err) {
            this.#logger?.(log_js_1.LogType.debugError, err);
            if (!this.#isExpectedError(err)) {
                throw err;
            }
        }
    }
    async toggleSetCacheDisabled(disable) {
        const defaultCacheDisabled = this.#networkStorage.defaultCacheBehavior === 'bypass';
        const cacheDisabled = disable ?? defaultCacheDisabled;
        if (this.#cacheDisableState === cacheDisabled) {
            return;
        }
        this.#cacheDisableState = cacheDisabled;
        try {
            await this.#cdpClient.sendCommand('Network.setCacheDisabled', {
                cacheDisabled,
            });
        }
        catch (err) {
            this.#logger?.(log_js_1.LogType.debugError, err);
            this.#cacheDisableState = !cacheDisabled;
            if (!this.#isExpectedError(err)) {
                throw err;
            }
        }
    }
    async toggleDeviceAccessIfNeeded() {
        const enabled = this.isSubscribedTo(chromium_bidi_js_1.Bluetooth.EventNames.RequestDevicePromptUpdated);
        if (this.#deviceAccessEnabled === enabled) {
            return;
        }
        this.#deviceAccessEnabled = enabled;
        try {
            await this.#cdpClient.sendCommand(enabled ? 'DeviceAccess.enable' : 'DeviceAccess.disable');
        }
        catch (err) {
            this.#logger?.(log_js_1.LogType.debugError, err);
            this.#deviceAccessEnabled = !enabled;
            if (!this.#isExpectedError(err)) {
                throw err;
            }
        }
    }
    /**
     * Heuristic checking if the error is due to the session being closed. If so, ignore the
     * error.
     */
    #isExpectedError(err) {
        const error = err;
        return ((error.code === -32001 &&
            error.message === 'Session with given id not found.') ||
            this.#cdpClient.isCloseError(err));
    }
    #setEventListeners() {
        this.#cdpClient.on('Network.requestWillBeSent', (eventParams) => {
            if (eventParams.loaderId === eventParams.requestId) {
                this.emit("frameStartedNavigating" /* TargetEvents.FrameStartedNavigating */, {
                    loaderId: eventParams.loaderId,
                    url: eventParams.request.url,
                    frameId: eventParams.frameId,
                });
            }
        });
        this.#cdpClient.on('*', (event, params) => {
            // We may encounter uses for EventEmitter other than CDP events,
            // which we want to skip.
            if (typeof event !== 'string') {
                return;
            }
            this.#eventManager.registerEvent({
                type: 'event',
                method: `goog:cdp.${event}`,
                params: {
                    event,
                    params,
                    session: this.cdpSessionId,
                },
            }, this.id);
            // Duplicate the event to the deprecated event name.
            // https://github.com/GoogleChromeLabs/chromium-bidi/issues/2844
            this.#eventManager.registerEvent({
                type: 'event',
                method: `cdp.${event}`,
                params: {
                    event,
                    params,
                    session: this.cdpSessionId,
                },
            }, this.id);
        });
    }
    async #enableFetch(stages) {
        const patterns = [];
        if (stages.request || stages.auth) {
            // CDP quirk we need request interception when we intercept auth
            patterns.push({
                urlPattern: '*',
                requestStage: 'Request',
            });
        }
        if (stages.response) {
            patterns.push({
                urlPattern: '*',
                requestStage: 'Response',
            });
        }
        if (patterns.length) {
            const oldStages = this.#fetchDomainStages;
            this.#fetchDomainStages = stages;
            try {
                await this.#cdpClient.sendCommand('Fetch.enable', {
                    patterns,
                    handleAuthRequests: stages.auth,
                });
            }
            catch {
                this.#fetchDomainStages = oldStages;
            }
        }
    }
    async #disableFetch() {
        const blockedRequest = this.#networkStorage
            .getRequestsByTarget(this)
            .filter((request) => request.interceptPhase);
        if (blockedRequest.length === 0) {
            this.#fetchDomainStages = {
                request: false,
                response: false,
                auth: false,
            };
            await this.#cdpClient.sendCommand('Fetch.disable');
        }
    }
    async toggleNetwork() {
        const stages = this.#networkStorage.getInterceptionStages(this.topLevelId);
        const fetchEnable = Object.values(stages).some((value) => value);
        const fetchChanged = this.#fetchDomainStages.request !== stages.request ||
            this.#fetchDomainStages.response !== stages.response ||
            this.#fetchDomainStages.auth !== stages.auth;
        this.#logger?.(log_js_1.LogType.debugInfo, 'Toggle Network', `Fetch (${fetchEnable}) ${fetchChanged}`);
        if (fetchEnable && fetchChanged) {
            await this.#enableFetch(stages);
        }
        if (!fetchEnable && fetchChanged) {
            await this.#disableFetch();
        }
    }
    /**
     * All the ProxyChannels from all the preload scripts of the given
     * BrowsingContext.
     */
    getChannels() {
        return this.#preloadScriptStorage
            .find()
            .flatMap((script) => script.channels);
    }
    /** Loads all top-level preload scripts. */
    async #initAndEvaluatePreloadScripts() {
        await Promise.all(this.#preloadScriptStorage
            .find({
            // Needed for OOPIF
            targetId: this.topLevelId,
        })
            .map((script) => {
            return script.initInTarget(this, true);
        }));
    }
    get topLevelId() {
        return (this.#browsingContextStorage.findTopLevelContextId(this.id) ?? this.id);
    }
    isSubscribedTo(moduleOrEvent) {
        return this.#eventManager.subscriptionManager.isSubscribedTo(moduleOrEvent, this.topLevelId);
    }
}
exports.CdpTarget = CdpTarget;
//# sourceMappingURL=CdpTarget.js.map