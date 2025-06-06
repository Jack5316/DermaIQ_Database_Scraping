"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true
});
exports.toEqual = toEqual;
var _utils = require("playwright-core/lib/utils");
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

// Omit colon and one or more spaces, so can call getLabelPrinter.
const EXPECTED_LABEL = 'Expected';
const RECEIVED_LABEL = 'Received';
async function toEqual(matcherName, receiver, receiverType, query, expected, options = {}) {
  var _options$timeout;
  (0, _util.expectTypes)(receiver, [receiverType], matcherName);
  const matcherOptions = {
    comment: options.contains ? '' : 'deep equality',
    isNot: this.isNot,
    promise: this.promise
  };
  const timeout = (_options$timeout = options.timeout) !== null && _options$timeout !== void 0 ? _options$timeout : this.timeout;
  const {
    matches: pass,
    received,
    log,
    timedOut
  } = await query(!!this.isNot, timeout);
  if (pass === !this.isNot) {
    return {
      name: matcherName,
      message: () => '',
      pass,
      expected
    };
  }
  let printedReceived;
  let printedExpected;
  let printedDiff;
  if (pass) {
    printedExpected = `Expected: not ${this.utils.printExpected(expected)}`;
    printedReceived = `Received: ${this.utils.printReceived(received)}`;
  } else if (Array.isArray(expected) && Array.isArray(received)) {
    const normalizedExpected = expected.map((exp, index) => {
      const rec = received[index];
      if ((0, _utils.isRegExp)(exp)) return exp.test(rec) ? rec : exp;
      return exp;
    });
    printedDiff = this.utils.printDiffOrStringify(normalizedExpected, received, EXPECTED_LABEL, RECEIVED_LABEL, false);
  } else {
    printedDiff = this.utils.printDiffOrStringify(expected, received, EXPECTED_LABEL, RECEIVED_LABEL, false);
  }
  const message = () => {
    const header = (0, _matcherHint.matcherHint)(this, receiver, matcherName, 'locator', undefined, matcherOptions, timedOut ? timeout : undefined);
    const details = printedDiff || `${printedExpected}\n${printedReceived}`;
    return `${header}${details}${(0, _util.callLogText)(log)}`;
  };
  // Passing the actual and expected objects so that a custom reporter
  // could access them, for example in order to display a custom visual diff,
  // or create a different error message
  return {
    actual: received,
    expected,
    message,
    name: matcherName,
    pass,
    log,
    timeout: timedOut ? timeout : undefined
  };
}