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
import type { Browser, BrowsingContext, Cdp, Input, Network, Script, Session, Storage, Permissions, Bluetooth, WebExtension } from '../protocol/protocol.js';
import type { BidiCommandParameterParser } from './BidiParser.js';
export declare class BidiNoOpParser implements BidiCommandParameterParser {
    parseHandleRequestDevicePromptParams(params: unknown): Bluetooth.HandleRequestDevicePromptParameters;
    parseSimulateAdapterParameters(params: unknown): Bluetooth.SimulateAdapterParameters;
    parseSimulateAdvertisementParameters(params: unknown): Bluetooth.SimulateAdvertisementParameters;
    parseSimulatePreconnectedPeripheralParameters(params: unknown): Bluetooth.SimulatePreconnectedPeripheralParameters;
    parseRemoveUserContextParams(params: unknown): Browser.RemoveUserContextParameters;
    parseActivateParams(params: unknown): BrowsingContext.ActivateParameters;
    parseCaptureScreenshotParams(params: unknown): BrowsingContext.CaptureScreenshotParameters;
    parseCloseParams(params: unknown): BrowsingContext.CloseParameters;
    parseCreateParams(params: unknown): BrowsingContext.CreateParameters;
    parseGetTreeParams(params: unknown): BrowsingContext.GetTreeParameters;
    parseHandleUserPromptParams(params: unknown): BrowsingContext.HandleUserPromptParameters;
    parseLocateNodesParams(params: unknown): BrowsingContext.LocateNodesParameters;
    parseNavigateParams(params: unknown): BrowsingContext.NavigateParameters;
    parsePrintParams(params: unknown): BrowsingContext.PrintParameters;
    parseReloadParams(params: unknown): BrowsingContext.ReloadParameters;
    parseSetViewportParams(params: unknown): BrowsingContext.SetViewportParameters;
    parseTraverseHistoryParams(params: unknown): BrowsingContext.TraverseHistoryParameters;
    parseGetSessionParams(params: unknown): Cdp.GetSessionParameters;
    parseResolveRealmParams(params: unknown): Cdp.ResolveRealmParameters;
    parseSendCommandParams(params: unknown): Cdp.SendCommandParameters;
    parseAddPreloadScriptParams(params: unknown): Script.AddPreloadScriptParameters;
    parseCallFunctionParams(params: unknown): Script.CallFunctionParameters;
    parseDisownParams(params: unknown): Script.DisownParameters;
    parseEvaluateParams(params: unknown): Script.EvaluateParameters;
    parseGetRealmsParams(params: unknown): Script.GetRealmsParameters;
    parseRemovePreloadScriptParams(params: unknown): Script.RemovePreloadScriptParameters;
    parsePerformActionsParams(params: unknown): Input.PerformActionsParameters;
    parseReleaseActionsParams(params: unknown): Input.ReleaseActionsParameters;
    parseSetFilesParams(params: unknown): Input.SetFilesParameters;
    parseAddInterceptParams(params: unknown): Network.AddInterceptParameters;
    parseContinueRequestParams(params: unknown): Network.ContinueRequestParameters;
    parseContinueResponseParams(params: unknown): Network.ContinueResponseParameters;
    parseContinueWithAuthParams(params: unknown): Network.ContinueWithAuthParameters;
    parseFailRequestParams(params: unknown): Network.FailRequestParameters;
    parseProvideResponseParams(params: unknown): Network.ProvideResponseParameters;
    parseRemoveInterceptParams(params: unknown): Network.RemoveInterceptParameters;
    parseSetCacheBehavior(params: unknown): Network.SetCacheBehaviorParameters;
    parseSetPermissionsParams(params: unknown): Permissions.SetPermissionParameters;
    parseSubscribeParams(params: unknown): Session.SubscriptionRequest;
    parseUnsubscribeParams(params: unknown): Session.UnsubscribeByAttributesRequest | Session.UnsubscribeByIdRequest;
    parseDeleteCookiesParams(params: unknown): Storage.DeleteCookiesParameters;
    parseGetCookiesParams(params: unknown): Storage.GetCookiesParameters;
    parseSetCookieParams(params: unknown): Storage.SetCookieParameters;
    parseInstallParams(params: unknown): WebExtension.InstallParameters;
    parseUninstallParams(params: unknown): WebExtension.UninstallParameters;
}
