"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.execArgvWithExperimentalLoaderOptions = execArgvWithExperimentalLoaderOptions;
exports.execArgvWithoutExperimentalLoaderOptions = execArgvWithoutExperimentalLoaderOptions;
var _url = _interopRequireDefault(require("url"));
function _interopRequireDefault(e) { return e && e.__esModule ? e : { default: e }; }
/**
 * Copyright (c) Microsoft Corporation.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

const kExperimentalLoaderOptions = ['--no-warnings', `--experimental-loader=${_url.default.pathToFileURL(require.resolve('playwright/lib/transform/esmLoader')).toString()}`];
function execArgvWithExperimentalLoaderOptions() {
  return [...process.execArgv, ...kExperimentalLoaderOptions];
}
function execArgvWithoutExperimentalLoaderOptions() {
  return process.execArgv.filter(arg => !kExperimentalLoaderOptions.includes(arg));
}