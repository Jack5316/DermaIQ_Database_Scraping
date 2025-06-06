"use strict";
/**
 * Copyright 2023 Google LLC.
 * Copyright (c) Microsoft Corporation.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ScriptProcessor = void 0;
const protocol_js_1 = require("../../../protocol/protocol.js");
const PreloadScript_js_1 = require("./PreloadScript.js");
class ScriptProcessor {
    #eventManager;
    #browsingContextStorage;
    #realmStorage;
    #preloadScriptStorage;
    #userContextStorage;
    #logger;
    constructor(eventManager, browsingContextStorage, realmStorage, preloadScriptStorage, userContextStorage, logger) {
        this.#browsingContextStorage = browsingContextStorage;
        this.#realmStorage = realmStorage;
        this.#preloadScriptStorage = preloadScriptStorage;
        this.#userContextStorage = userContextStorage;
        this.#logger = logger;
        this.#eventManager = eventManager;
        this.#eventManager.addSubscribeHook(protocol_js_1.ChromiumBidi.Script.EventNames.RealmCreated, this.#onRealmCreatedSubscribeHook.bind(this));
    }
    #onRealmCreatedSubscribeHook(contextId) {
        const context = this.#browsingContextStorage.getContext(contextId);
        const contextsToReport = [
            context,
            ...this.#browsingContextStorage.getContext(contextId).allChildren,
        ];
        const realms = new Set();
        for (const reportContext of contextsToReport) {
            const realmsForContext = this.#realmStorage.findRealms({
                browsingContextId: reportContext.id,
            });
            for (const realm of realmsForContext) {
                realms.add(realm);
            }
        }
        for (const realm of realms) {
            this.#eventManager.registerEvent({
                type: 'event',
                method: protocol_js_1.ChromiumBidi.Script.EventNames.RealmCreated,
                params: realm.realmInfo,
            }, context.id);
        }
        return Promise.resolve();
    }
    async addPreloadScript(params) {
        if (params.userContexts?.length && params.contexts?.length) {
            throw new protocol_js_1.InvalidArgumentException('Both userContexts and contexts cannot be specified.');
        }
        const userContexts = await this.#userContextStorage.verifyUserContextIdList(params.userContexts ?? []);
        const browsingContexts = this.#browsingContextStorage.verifyTopLevelContextsList(params.contexts);
        const preloadScript = new PreloadScript_js_1.PreloadScript(params, this.#logger);
        this.#preloadScriptStorage.add(preloadScript);
        let contextsToRunIn = [];
        if (userContexts.size) {
            contextsToRunIn = this.#browsingContextStorage
                .getTopLevelContexts()
                .filter((context) => {
                return userContexts.has(context.userContext);
            });
        }
        else if (browsingContexts.size) {
            contextsToRunIn = [...browsingContexts.values()];
        }
        else {
            contextsToRunIn = this.#browsingContextStorage.getTopLevelContexts();
        }
        const cdpTargets = new Set(contextsToRunIn.map((context) => context.cdpTarget));
        await preloadScript.initInTargets(cdpTargets, false);
        return {
            script: preloadScript.id,
        };
    }
    async removePreloadScript(params) {
        const { script: id } = params;
        const script = this.#preloadScriptStorage.getPreloadScript(id);
        await script.remove();
        this.#preloadScriptStorage.remove(id);
        return {};
    }
    async callFunction(params) {
        const realm = await this.#getRealm(params.target);
        return await realm.callFunction(params.functionDeclaration, params.awaitPromise, params.this, params.arguments, params.resultOwnership, params.serializationOptions, params.userActivation);
    }
    async evaluate(params) {
        const realm = await this.#getRealm(params.target);
        return await realm.evaluate(params.expression, params.awaitPromise, params.resultOwnership, params.serializationOptions, params.userActivation);
    }
    async disown(params) {
        const realm = await this.#getRealm(params.target);
        await Promise.all(params.handles.map(async (handle) => await realm.disown(handle)));
        return {};
    }
    getRealms(params) {
        if (params.context !== undefined) {
            // Make sure the context is known.
            this.#browsingContextStorage.getContext(params.context);
        }
        const realms = this.#realmStorage
            .findRealms({
            browsingContextId: params.context,
            type: params.type,
        })
            .map((realm) => realm.realmInfo);
        return { realms };
    }
    async #getRealm(target) {
        if ('context' in target) {
            const context = this.#browsingContextStorage.getContext(target.context);
            return await context.getOrCreateSandbox(target.sandbox);
        }
        return this.#realmStorage.getRealm({
            realmId: target.realm,
        });
    }
}
exports.ScriptProcessor = ScriptProcessor;
//# sourceMappingURL=ScriptProcessor.js.map