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
exports.EVENT_NAMES = exports.Bluetooth = exports.Network = exports.BrowsingContext = exports.Log = exports.Script = exports.BiDiModule = void 0;
// keep-sorted end
var BiDiModule;
(function (BiDiModule) {
    // keep-sorted start
    BiDiModule["Bluetooth"] = "bluetooth";
    BiDiModule["Browser"] = "browser";
    BiDiModule["BrowsingContext"] = "browsingContext";
    BiDiModule["Cdp"] = "goog:cdp";
    BiDiModule["DeprecatedCdp"] = "cdp";
    BiDiModule["Input"] = "input";
    BiDiModule["Log"] = "log";
    BiDiModule["Network"] = "network";
    BiDiModule["Script"] = "script";
    BiDiModule["Session"] = "session";
    // keep-sorted end
})(BiDiModule || (exports.BiDiModule = BiDiModule = {}));
var Script;
(function (Script) {
    let EventNames;
    (function (EventNames) {
        // keep-sorted start
        EventNames["Message"] = "script.message";
        EventNames["RealmCreated"] = "script.realmCreated";
        EventNames["RealmDestroyed"] = "script.realmDestroyed";
        // keep-sorted end
    })(EventNames = Script.EventNames || (Script.EventNames = {}));
})(Script || (exports.Script = Script = {}));
var Log;
(function (Log) {
    let EventNames;
    (function (EventNames) {
        EventNames["LogEntryAdded"] = "log.entryAdded";
    })(EventNames = Log.EventNames || (Log.EventNames = {}));
})(Log || (exports.Log = Log = {}));
var BrowsingContext;
(function (BrowsingContext) {
    let EventNames;
    (function (EventNames) {
        // keep-sorted start
        EventNames["ContextCreated"] = "browsingContext.contextCreated";
        EventNames["ContextDestroyed"] = "browsingContext.contextDestroyed";
        EventNames["DomContentLoaded"] = "browsingContext.domContentLoaded";
        EventNames["DownloadWillBegin"] = "browsingContext.downloadWillBegin";
        EventNames["FragmentNavigated"] = "browsingContext.fragmentNavigated";
        EventNames["HistoryUpdated"] = "browsingContext.historyUpdated";
        EventNames["Load"] = "browsingContext.load";
        EventNames["NavigationAborted"] = "browsingContext.navigationAborted";
        EventNames["NavigationCommitted"] = "browsingContext.navigationCommitted";
        EventNames["NavigationFailed"] = "browsingContext.navigationFailed";
        EventNames["NavigationStarted"] = "browsingContext.navigationStarted";
        EventNames["UserPromptClosed"] = "browsingContext.userPromptClosed";
        EventNames["UserPromptOpened"] = "browsingContext.userPromptOpened";
        // keep-sorted end
    })(EventNames = BrowsingContext.EventNames || (BrowsingContext.EventNames = {}));
})(BrowsingContext || (exports.BrowsingContext = BrowsingContext = {}));
var Network;
(function (Network) {
    let EventNames;
    (function (EventNames) {
        // keep-sorted start
        EventNames["AuthRequired"] = "network.authRequired";
        EventNames["BeforeRequestSent"] = "network.beforeRequestSent";
        EventNames["FetchError"] = "network.fetchError";
        EventNames["ResponseCompleted"] = "network.responseCompleted";
        EventNames["ResponseStarted"] = "network.responseStarted";
        // keep-sorted end
    })(EventNames = Network.EventNames || (Network.EventNames = {}));
})(Network || (exports.Network = Network = {}));
var Bluetooth;
(function (Bluetooth) {
    let EventNames;
    (function (EventNames) {
        EventNames["RequestDevicePromptUpdated"] = "bluetooth.requestDevicePromptUpdated";
    })(EventNames = Bluetooth.EventNames || (Bluetooth.EventNames = {}));
})(Bluetooth || (exports.Bluetooth = Bluetooth = {}));
exports.EVENT_NAMES = new Set([
    // keep-sorted start
    ...Object.values(BiDiModule),
    ...Object.values(Bluetooth.EventNames),
    ...Object.values(BrowsingContext.EventNames),
    ...Object.values(Log.EventNames),
    ...Object.values(Network.EventNames),
    ...Object.values(Script.EventNames),
    // keep-sorted end
]);
//# sourceMappingURL=chromium-bidi.js.map