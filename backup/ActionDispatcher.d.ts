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
import type { BrowsingContextImpl } from '../context/BrowsingContextImpl.js';
import type { BrowsingContextStorage } from '../context/BrowsingContextStorage.js';
import type { ActionOption } from './ActionOption.js';
import type { InputState } from './InputState.js';
export declare class ActionDispatcher {
    #private;
    static isMacOS: (context: BrowsingContextImpl) => Promise<boolean>;
    constructor(inputState: InputState, browsingContextStorage: BrowsingContextStorage, contextId: string, isMacOS: boolean);
    dispatchActions(optionsByTick: readonly (readonly Readonly<ActionOption>[])[]): Promise<void>;
    dispatchTickActions(options: readonly Readonly<ActionOption>[]): Promise<void>;
}
