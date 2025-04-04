"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.toBeTruthy = toBeTruthy;
var _util = require("../util");
var _matcherHint = require("./matcherHint");
/**
 * Copyright Microsoft Corporation. All rights reserved.
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

async function toBeTruthy(matcherName, receiver, receiverType, expected, arg, query, options = {}) {
  var _options$timeout;
  (0, _util.expectTypes)(receiver, [receiverType], matcherName);
  const matcherOptions = {
    isNot: this.isNot,
    promise: this.promise
  };
  const timeout = (_options$timeout = options.timeout) !== null && _options$timeout !== void 0 ? _options$timeout : this.timeout;
  const {
    matches: pass,
    log,
    timedOut,
    received
  } = await query(!!this.isNot, timeout);
  if (pass === !this.isNot) {
    return {
      name: matcherName,
      message: () => '',
      pass,
      expected
    };
  }
  const notFound = received === _matcherHint.kNoElementsFoundError ? received : undefined;
  let printedReceived;
  let printedExpected;
  if (pass) {
    printedExpected = `Expected: not ${expected}`;
    printedReceived = `Received: ${notFound ? _matcherHint.kNoElementsFoundError : expected}`;
  } else {
    printedExpected = `Expected: ${expected}`;
    printedReceived = `Received: ${notFound ? _matcherHint.kNoElementsFoundError : received}`;
  }
  const message = () => {
    const header = (0, _matcherHint.matcherHint)(this, receiver, matcherName, 'locator', arg, matcherOptions, timedOut ? timeout : undefined);
    const logText = (0, _util.callLogText)(log);
    return `${header}${printedExpected}\n${printedReceived}${logText}`;
  };
  return {
    message,
    pass,
    actual: received,
    name: matcherName,
    expected,
    log,
    timeout: timedOut ? timeout : undefined
  };
}