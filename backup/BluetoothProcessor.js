"use strict";
/**
 * Copyright 2024 Google LLC.
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
exports.BluetoothProcessor = void 0;
const protocol_js_1 = require("../../../protocol/protocol.js");
class BluetoothProcessor {
    #eventManager;
    #browsingContextStorage;
    constructor(eventManager, browsingContextStorage) {
        this.#eventManager = eventManager;
        this.#browsingContextStorage = browsingContextStorage;
    }
    async simulateAdapter(params) {
        if (params.type !== 'create') {
            // http://b/398026399
            throw new protocol_js_1.UnsupportedOperationException(`Simulate type "${params.type}" is not supported. Only create type is supported`);
        }
        if (params.state === undefined) {
            // The bluetooth.simulateAdapter Command
            // Step 4.2. If params["state"] does not exist, return error with error code invalid argument.
            // https://webbluetoothcg.github.io/web-bluetooth/#bluetooth-simulateAdapter-command
            throw new protocol_js_1.InvalidArgumentException(`Parameter "state" is required for creating a Bluetooth adapter`);
        }
        const context = this.#browsingContextStorage.getContext(params.context);
        // Bluetooth spec requires overriding the existing adapter (step 6). From the CDP
        // perspective, we need to disable the emulation first.
        // https://webbluetoothcg.github.io/web-bluetooth/#bluetooth-simulateAdapter-command
        await context.cdpTarget.browserCdpClient.sendCommand('BluetoothEmulation.disable');
        await context.cdpTarget.browserCdpClient.sendCommand('BluetoothEmulation.enable', {
            state: params.state,
        });
        return {};
    }
    async simulatePreconnectedPeripheral(params) {
        const context = this.#browsingContextStorage.getContext(params.context);
        await context.cdpTarget.browserCdpClient.sendCommand('BluetoothEmulation.simulatePreconnectedPeripheral', {
            address: params.address,
            name: params.name,
            knownServiceUuids: params.knownServiceUuids,
            manufacturerData: params.manufacturerData,
        });
        return {};
    }
    async simulateAdvertisement(params) {
        const context = this.#browsingContextStorage.getContext(params.context);
        await context.cdpTarget.browserCdpClient.sendCommand('BluetoothEmulation.simulateAdvertisement', {
            entry: params.scanEntry,
        });
        return {};
    }
    onCdpTargetCreated(cdpTarget) {
        cdpTarget.cdpClient.on('DeviceAccess.deviceRequestPrompted', (event) => {
            this.#eventManager.registerEvent({
                type: 'event',
                method: 'bluetooth.requestDevicePromptUpdated',
                params: {
                    context: cdpTarget.id,
                    prompt: event.id,
                    devices: event.devices,
                },
            }, cdpTarget.id);
        });
    }
    async handleRequestDevicePrompt(params) {
        const context = this.#browsingContextStorage.getContext(params.context);
        if (params.accept) {
            await context.cdpTarget.cdpClient.sendCommand('DeviceAccess.selectPrompt', {
                id: params.prompt,
                deviceId: params.device,
            });
        }
        else {
            await context.cdpTarget.cdpClient.sendCommand('DeviceAccess.cancelPrompt', {
                id: params.prompt,
            });
        }
        return {};
    }
}
exports.BluetoothProcessor = BluetoothProcessor;
//# sourceMappingURL=BluetoothProcessor.js.map