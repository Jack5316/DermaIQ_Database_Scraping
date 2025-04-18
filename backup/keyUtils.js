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
exports.getNormalizedKey = getNormalizedKey;
exports.getKeyCode = getKeyCode;
exports.getKeyLocation = getKeyLocation;
/**
 * Returns the normalized key value for a given key according to the table:
 * https://w3c.github.io/webdriver/#dfn-normalized-key-value
 */
function getNormalizedKey(value) {
    switch (value) {
        case '\uE000':
            return 'Unidentified';
        case '\uE001':
            return 'Cancel';
        case '\uE002':
            return 'Help';
        case '\uE003':
            return 'Backspace';
        case '\uE004':
            return 'Tab';
        case '\uE005':
            return 'Clear';
        // Specification declares the '\uE006' to be `Return`, but it is not supported by
        // Chrome, so fall back to `Enter`, which aligns with WPT.
        case '\uE006':
        case '\uE007':
            return 'Enter';
        case '\uE008':
            return 'Shift';
        case '\uE009':
            return 'Control';
        case '\uE00A':
            return 'Alt';
        case '\uE00B':
            return 'Pause';
        case '\uE00C':
            return 'Escape';
        case '\uE00D':
            return ' ';
        case '\uE00E':
            return 'PageUp';
        case '\uE00F':
            return 'PageDown';
        case '\uE010':
            return 'End';
        case '\uE011':
            return 'Home';
        case '\uE012':
            return 'ArrowLeft';
        case '\uE013':
            return 'ArrowUp';
        case '\uE014':
            return 'ArrowRight';
        case '\uE015':
            return 'ArrowDown';
        case '\uE016':
            return 'Insert';
        case '\uE017':
            return 'Delete';
        case '\uE018':
            return ';';
        case '\uE019':
            return '=';
        case '\uE01A':
            return '0';
        case '\uE01B':
            return '1';
        case '\uE01C':
            return '2';
        case '\uE01D':
            return '3';
        case '\uE01E':
            return '4';
        case '\uE01F':
            return '5';
        case '\uE020':
            return '6';
        case '\uE021':
            return '7';
        case '\uE022':
            return '8';
        case '\uE023':
            return '9';
        case '\uE024':
            return '*';
        case '\uE025':
            return '+';
        case '\uE026':
            return ',';
        case '\uE027':
            return '-';
        case '\uE028':
            return '.';
        case '\uE029':
            return '/';
        case '\uE031':
            return 'F1';
        case '\uE032':
            return 'F2';
        case '\uE033':
            return 'F3';
        case '\uE034':
            return 'F4';
        case '\uE035':
            return 'F5';
        case '\uE036':
            return 'F6';
        case '\uE037':
            return 'F7';
        case '\uE038':
            return 'F8';
        case '\uE039':
            return 'F9';
        case '\uE03A':
            return 'F10';
        case '\uE03B':
            return 'F11';
        case '\uE03C':
            return 'F12';
        case '\uE03D':
            return 'Meta';
        case '\uE040':
            return 'ZenkakuHankaku';
        case '\uE050':
            return 'Shift';
        case '\uE051':
            return 'Control';
        case '\uE052':
            return 'Alt';
        case '\uE053':
            return 'Meta';
        case '\uE054':
            return 'PageUp';
        case '\uE055':
            return 'PageDown';
        case '\uE056':
            return 'End';
        case '\uE057':
            return 'Home';
        case '\uE058':
            return 'ArrowLeft';
        case '\uE059':
            return 'ArrowUp';
        case '\uE05A':
            return 'ArrowRight';
        case '\uE05B':
            return 'ArrowDown';
        case '\uE05C':
            return 'Insert';
        case '\uE05D':
            return 'Delete';
        default:
            return value;
    }
}
/**
 * Returns the key code for a given key according to the table:
 * https://w3c.github.io/webdriver/#dfn-shifted-character
 */
function getKeyCode(key) {
    switch (key) {
        case '`':
        case '~':
            return 'Backquote';
        case '\\':
        case '|':
            return 'Backslash';
        case '\uE003':
            return 'Backspace';
        case '[':
        case '{':
            return 'BracketLeft';
        case ']':
        case '}':
            return 'BracketRight';
        case ',':
        case '<':
            return 'Comma';
        case '0':
        case ')':
            return 'Digit0';
        case '1':
        case '!':
            return 'Digit1';
        case '2':
        case '@':
            return 'Digit2';
        case '3':
        case '#':
            return 'Digit3';
        case '4':
        case '$':
            return 'Digit4';
        case '5':
        case '%':
            return 'Digit5';
        case '6':
        case '^':
            return 'Digit6';
        case '7':
        case '&':
            return 'Digit7';
        case '8':
        case '*':
            return 'Digit8';
        case '9':
        case '(':
            return 'Digit9';
        case '=':
        case '+':
            return 'Equal';
        // The spec declares the '<' to be `IntlBackslash` as well, but it is already covered
        // in the `Comma` above.
        case '>':
            return 'IntlBackslash';
        case 'a':
        case 'A':
            return 'KeyA';
        case 'b':
        case 'B':
            return 'KeyB';
        case 'c':
        case 'C':
            return 'KeyC';
        case 'd':
        case 'D':
            return 'KeyD';
        case 'e':
        case 'E':
            return 'KeyE';
        case 'f':
        case 'F':
            return 'KeyF';
        case 'g':
        case 'G':
            return 'KeyG';
        case 'h':
        case 'H':
            return 'KeyH';
        case 'i':
        case 'I':
            return 'KeyI';
        case 'j':
        case 'J':
            return 'KeyJ';
        case 'k':
        case 'K':
            return 'KeyK';
        case 'l':
        case 'L':
            return 'KeyL';
        case 'm':
        case 'M':
            return 'KeyM';
        case 'n':
        case 'N':
            return 'KeyN';
        case 'o':
        case 'O':
            return 'KeyO';
        case 'p':
        case 'P':
            return 'KeyP';
        case 'q':
        case 'Q':
            return 'KeyQ';
        case 'r':
        case 'R':
            return 'KeyR';
        case 's':
        case 'S':
            return 'KeyS';
        case 't':
        case 'T':
            return 'KeyT';
        case 'u':
        case 'U':
            return 'KeyU';
        case 'v':
        case 'V':
            return 'KeyV';
        case 'w':
        case 'W':
            return 'KeyW';
        case 'x':
        case 'X':
            return 'KeyX';
        case 'y':
        case 'Y':
            return 'KeyY';
        case 'z':
        case 'Z':
            return 'KeyZ';
        case '-':
        case '_':
            return 'Minus';
        case '.':
            return 'Period';
        case "'":
        case '"':
            return 'Quote';
        case ';':
        case ':':
            return 'Semicolon';
        case '/':
        case '?':
            return 'Slash';
        case '\uE00A':
            return 'AltLeft';
        case '\uE052':
            return 'AltRight';
        case '\uE009':
            return 'ControlLeft';
        case '\uE051':
            return 'ControlRight';
        case '\uE006':
            return 'Enter';
        case '\uE00B':
            return 'Pause';
        case '\uE03D':
            return 'MetaLeft';
        case '\uE053':
            return 'MetaRight';
        case '\uE008':
            return 'ShiftLeft';
        case '\uE050':
            return 'ShiftRight';
        case ' ':
        case '\uE00D':
            return 'Space';
        case '\uE004':
            return 'Tab';
        case '\uE017':
            return 'Delete';
        case '\uE010':
            return 'End';
        case '\uE002':
            return 'Help';
        case '\uE011':
            return 'Home';
        case '\uE016':
            return 'Insert';
        case '\uE00F':
            return 'PageDown';
        case '\uE00E':
            return 'PageUp';
        case '\uE015':
            return 'ArrowDown';
        case '\uE012':
            return 'ArrowLeft';
        case '\uE014':
            return 'ArrowRight';
        case '\uE013':
            return 'ArrowUp';
        case '\uE00C':
            return 'Escape';
        case '\uE031':
            return 'F1';
        case '\uE032':
            return 'F2';
        case '\uE033':
            return 'F3';
        case '\uE034':
            return 'F4';
        case '\uE035':
            return 'F5';
        case '\uE036':
            return 'F6';
        case '\uE037':
            return 'F7';
        case '\uE038':
            return 'F8';
        case '\uE039':
            return 'F9';
        case '\uE03A':
            return 'F10';
        case '\uE03B':
            return 'F11';
        case '\uE03C':
            return 'F12';
        case '\uE019':
            return 'NumpadEqual';
        case '\uE01A':
        case '\uE05C':
            return 'Numpad0';
        case '\uE01B':
        case '\uE056':
            return 'Numpad1';
        case '\uE01C':
        case '\uE05B':
            return 'Numpad2';
        case '\uE01D':
        case '\uE055':
            return 'Numpad3';
        case '\uE01E':
        case '\uE058':
            return 'Numpad4';
        case '\uE01F':
            return 'Numpad5';
        case '\uE020':
        case '\uE05A':
            return 'Numpad6';
        case '\uE021':
        case '\uE057':
            return 'Numpad7';
        case '\uE022':
        case '\uE059':
            return 'Numpad8';
        case '\uE023':
        case '\uE054':
            return 'Numpad9';
        case '\uE025':
            return 'NumpadAdd';
        case '\uE026':
            return 'NumpadComma';
        case '\uE028':
        case '\uE05D':
            return 'NumpadDecimal';
        case '\uE029':
            return 'NumpadDivide';
        case '\uE007':
            return 'NumpadEnter';
        case '\uE024':
            return 'NumpadMultiply';
        case '\uE027':
            return 'NumpadSubtract';
        default:
            return;
    }
}
/**
 * Returns the location of the key according to the table:
 * https://w3c.github.io/webdriver/#dfn-key-location
 */
function getKeyLocation(key) {
    switch (key) {
        case '\uE007':
        case '\uE008':
        case '\uE009':
        case '\uE00A':
        case '\uE03D':
            return 1;
        case '\uE019':
        case '\uE01A':
        case '\uE01B':
        case '\uE01C':
        case '\uE01D':
        case '\uE01E':
        case '\uE01F':
        case '\uE020':
        case '\uE021':
        case '\uE022':
        case '\uE023':
        case '\uE024':
        case '\uE025':
        case '\uE026':
        case '\uE027':
        case '\uE028':
        case '\uE029':
        case '\uE054':
        case '\uE055':
        case '\uE056':
        case '\uE057':
        case '\uE058':
        case '\uE059':
        case '\uE05A':
        case '\uE05B':
        case '\uE05C':
        case '\uE05D':
            return 3;
        case '\uE050':
        case '\uE051':
        case '\uE052':
        case '\uE053':
            return 2;
        default:
            return 0;
    }
}
//# sourceMappingURL=keyUtils.js.map