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
exports.SessionProcessor = void 0;
const protocol_js_1 = require("../../../protocol/protocol.js");
class SessionProcessor {
    #eventManager;
    #browserCdpClient;
    #initConnection;
    #created = false;
    constructor(eventManager, browserCdpClient, initConnection) {
        this.#eventManager = eventManager;
        this.#browserCdpClient = browserCdpClient;
        this.#initConnection = initConnection;
    }
    status() {
        return { ready: false, message: 'already connected' };
    }
    #mergeCapabilities(capabilitiesRequest) {
        // Roughly following https://www.w3.org/TR/webdriver2/#dfn-capabilities-processing.
        // Validations should already be done by the parser.
        const mergedCapabilities = [];
        for (const first of capabilitiesRequest.firstMatch ?? [{}]) {
            const result = {
                ...capabilitiesRequest.alwaysMatch,
            };
            for (const key of Object.keys(first)) {
                if (result[key] !== undefined) {
                    throw new protocol_js_1.InvalidArgumentException(`Capability ${key} in firstMatch is already defined in alwaysMatch`);
                }
                result[key] = first[key];
            }
            mergedCapabilities.push(result);
        }
        const match = mergedCapabilities.find((c) => c.browserName === 'chrome') ??
            mergedCapabilities[0] ??
            {};
        match.unhandledPromptBehavior = this.#getUnhandledPromptBehavior(match.unhandledPromptBehavior);
        return match;
    }
    #getUnhandledPromptBehavior(capabilityValue) {
        if (capabilityValue === undefined) {
            return undefined;
        }
        if (typeof capabilityValue === 'object') {
            // Do not validate capabilities. Incorrect ones will be ignored by Mapper.
            return capabilityValue;
        }
        if (typeof capabilityValue !== 'string') {
            throw new protocol_js_1.InvalidArgumentException(`Unexpected 'unhandledPromptBehavior' type: ${typeof capabilityValue}`);
        }
        switch (capabilityValue) {
            case 'accept':
            case 'accept and notify':
                return { default: "accept" /* Session.UserPromptHandlerType.Accept */ };
            case 'dismiss':
            case 'dismiss and notify':
                return { default: "dismiss" /* Session.UserPromptHandlerType.Dismiss */ };
            case 'ignore':
                return { default: "ignore" /* Session.UserPromptHandlerType.Ignore */ };
            default:
                throw new protocol_js_1.InvalidArgumentException(`Unexpected 'unhandledPromptBehavior' value: ${capabilityValue}`);
        }
    }
    async new(params) {
        if (this.#created) {
            throw new Error('Session has been already created.');
        }
        this.#created = true;
        const matchedCapabitlites = this.#mergeCapabilities(params.capabilities);
        await this.#initConnection(matchedCapabitlites);
        const version = await this.#browserCdpClient.sendCommand('Browser.getVersion');
        return {
            sessionId: 'unknown',
            capabilities: {
                ...matchedCapabitlites,
                acceptInsecureCerts: matchedCapabitlites.acceptInsecureCerts ?? false,
                browserName: version.product,
                browserVersion: version.revision,
                platformName: '',
                setWindowRect: false,
                webSocketUrl: '',
                userAgent: version.userAgent,
            },
        };
    }
    async subscribe(params, channel = {}) {
        const subscription = await this.#eventManager.subscribe(params.events, params.contexts ?? [], params.userContexts ?? [], channel);
        return {
            subscription,
        };
    }
    async unsubscribe(params, channel = {}) {
        if ('subscriptions' in params) {
            await this.#eventManager.unsubscribeByIds(params.subscriptions);
            return {};
        }
        await this.#eventManager.unsubscribe(params.events, params.contexts ?? [], channel);
        return {};
    }
}
exports.SessionProcessor = SessionProcessor;
//# sourceMappingURL=SessionProcessor.js.map