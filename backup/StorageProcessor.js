"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.StorageProcessor = void 0;
const protocol_js_1 = require("../../../protocol/protocol.js");
const assert_js_1 = require("../../../utils/assert.js");
const log_js_1 = require("../../../utils/log.js");
const NetworkProcessor_js_1 = require("../network/NetworkProcessor.js");
const NetworkUtils_js_1 = require("../network/NetworkUtils.js");
/**
 * Responsible for handling the `storage` module.
 */
class StorageProcessor {
    #browserCdpClient;
    #browsingContextStorage;
    #logger;
    constructor(browserCdpClient, browsingContextStorage, logger) {
        this.#browsingContextStorage = browsingContextStorage;
        this.#browserCdpClient = browserCdpClient;
        this.#logger = logger;
    }
    async deleteCookies(params) {
        const partitionKey = this.#expandStoragePartitionSpec(params.partition);
        let cdpResponse;
        try {
            cdpResponse = await this.#browserCdpClient.sendCommand('Storage.getCookies', {
                browserContextId: this.#getCdpBrowserContextId(partitionKey),
            });
        }
        catch (err) {
            if (this.#isNoSuchUserContextError(err)) {
                // If the user context is not found, special error is thrown.
                throw new protocol_js_1.NoSuchUserContextException(err.message);
            }
            throw err;
        }
        const cdpCookiesToDelete = cdpResponse.cookies
            .filter(
        // CDP's partition key is the source origin. If the request specifies the
        // `sourceOrigin` partition key, only cookies with the requested source origin
        // are returned.
        (c) => partitionKey.sourceOrigin === undefined ||
            c.partitionKey?.topLevelSite === partitionKey.sourceOrigin)
            .filter((cdpCookie) => {
            const bidiCookie = (0, NetworkUtils_js_1.cdpToBiDiCookie)(cdpCookie);
            return this.#matchCookie(bidiCookie, params.filter);
        })
            .map((cookie) => ({
            ...cookie,
            // Set expiry to pass date to delete the cookie.
            expires: 1,
        }));
        await this.#browserCdpClient.sendCommand('Storage.setCookies', {
            cookies: cdpCookiesToDelete,
            browserContextId: this.#getCdpBrowserContextId(partitionKey),
        });
        return {
            partitionKey,
        };
    }
    async getCookies(params) {
        const partitionKey = this.#expandStoragePartitionSpec(params.partition);
        let cdpResponse;
        try {
            cdpResponse = await this.#browserCdpClient.sendCommand('Storage.getCookies', {
                browserContextId: this.#getCdpBrowserContextId(partitionKey),
            });
        }
        catch (err) {
            if (this.#isNoSuchUserContextError(err)) {
                // If the user context is not found, special error is thrown.
                throw new protocol_js_1.NoSuchUserContextException(err.message);
            }
            throw err;
        }
        const filteredBiDiCookies = cdpResponse.cookies
            .filter(
        // CDP's partition key is the source origin. If the request specifies the
        // `sourceOrigin` partition key, only cookies with the requested source origin
        // are returned.
        (c) => partitionKey.sourceOrigin === undefined ||
            c.partitionKey?.topLevelSite === partitionKey.sourceOrigin)
            .map((c) => (0, NetworkUtils_js_1.cdpToBiDiCookie)(c))
            .filter((c) => this.#matchCookie(c, params.filter));
        return {
            cookies: filteredBiDiCookies,
            partitionKey,
        };
    }
    async setCookie(params) {
        const partitionKey = this.#expandStoragePartitionSpec(params.partition);
        const cdpCookie = (0, NetworkUtils_js_1.bidiToCdpCookie)(params, partitionKey);
        try {
            await this.#browserCdpClient.sendCommand('Storage.setCookies', {
                cookies: [cdpCookie],
                browserContextId: this.#getCdpBrowserContextId(partitionKey),
            });
        }
        catch (err) {
            if (this.#isNoSuchUserContextError(err)) {
                // If the user context is not found, special error is thrown.
                throw new protocol_js_1.NoSuchUserContextException(err.message);
            }
            this.#logger?.(log_js_1.LogType.debugError, err);
            throw new protocol_js_1.UnableToSetCookieException(err.toString());
        }
        return {
            partitionKey,
        };
    }
    #isNoSuchUserContextError(err) {
        // Heuristic to detect if the user context is not found.
        // See https://source.chromium.org/chromium/chromium/src/+/main:content/browser/devtools/protocol/browser_handler.cc;drc=a56154dd81e4679712422ac6eed2c9581cb51ab0;l=314
        return err.message?.startsWith('Failed to find browser context for id');
    }
    #getCdpBrowserContextId(partitionKey) {
        return partitionKey.userContext === 'default'
            ? undefined
            : partitionKey.userContext;
    }
    #expandStoragePartitionSpecByBrowsingContext(descriptor) {
        const browsingContextId = descriptor.context;
        const browsingContext = this.#browsingContextStorage.getContext(browsingContextId);
        // https://w3c.github.io/webdriver-bidi/#associated-storage-partition.
        // Each browsing context also has an associated storage partition, which is the
        // storage partition it uses to persist data. In Chromium it's a `BrowserContext`
        // which maps to BiDi `UserContext`.
        return {
            userContext: browsingContext.userContext,
        };
    }
    #expandStoragePartitionSpecByStorageKey(descriptor) {
        const unsupportedPartitionKeys = new Map();
        let sourceOrigin = descriptor.sourceOrigin;
        if (sourceOrigin !== undefined) {
            const url = NetworkProcessor_js_1.NetworkProcessor.parseUrlString(sourceOrigin);
            if (url.origin === 'null') {
                // Origin `null` is a special case for local pages.
                sourceOrigin = url.origin;
            }
            else {
                // Port is not supported in CDP Cookie's `partitionKey`, so it should be stripped
                // from the requested source origin.
                sourceOrigin = `${url.protocol}//${url.hostname}`;
            }
        }
        for (const [key, value] of Object.entries(descriptor)) {
            if (key !== undefined &&
                value !== undefined &&
                !['type', 'sourceOrigin', 'userContext'].includes(key)) {
                unsupportedPartitionKeys.set(key, value);
            }
        }
        if (unsupportedPartitionKeys.size > 0) {
            this.#logger?.(log_js_1.LogType.debugInfo, `Unsupported partition keys: ${JSON.stringify(Object.fromEntries(unsupportedPartitionKeys))}`);
        }
        // Set `userContext` to `default` if not provided, as it's required in Chromium.
        const userContext = descriptor.userContext ?? 'default';
        return {
            userContext,
            ...(sourceOrigin === undefined ? {} : { sourceOrigin }),
        };
    }
    #expandStoragePartitionSpec(partitionSpec) {
        if (partitionSpec === undefined) {
            // `userContext` is required in Chromium.
            return { userContext: 'default' };
        }
        if (partitionSpec.type === 'context') {
            return this.#expandStoragePartitionSpecByBrowsingContext(partitionSpec);
        }
        (0, assert_js_1.assert)(partitionSpec.type === 'storageKey', 'Unknown partition type');
        // Partition spec is a storage partition.
        // Let partition key be partition spec.
        return this.#expandStoragePartitionSpecByStorageKey(partitionSpec);
    }
    #matchCookie(cookie, filter) {
        if (filter === undefined) {
            return true;
        }
        return ((filter.domain === undefined || filter.domain === cookie.domain) &&
            (filter.name === undefined || filter.name === cookie.name) &&
            // `value` contains fields `type` and `value`.
            (filter.value === undefined ||
                (0, NetworkUtils_js_1.deserializeByteValue)(filter.value) ===
                    (0, NetworkUtils_js_1.deserializeByteValue)(cookie.value)) &&
            (filter.path === undefined || filter.path === cookie.path) &&
            (filter.size === undefined || filter.size === cookie.size) &&
            (filter.httpOnly === undefined || filter.httpOnly === cookie.httpOnly) &&
            (filter.secure === undefined || filter.secure === cookie.secure) &&
            (filter.sameSite === undefined || filter.sameSite === cookie.sameSite) &&
            (filter.expiry === undefined || filter.expiry === cookie.expiry));
    }
}
exports.StorageProcessor = StorageProcessor;
//# sourceMappingURL=StorageProcessor.js.map