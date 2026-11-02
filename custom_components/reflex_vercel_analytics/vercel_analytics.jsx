/**
 * React bridge between Reflex and @vercel/analytics (Vercel Web Analytics),
 * used by the `reflex-vercel-analytics` custom component.
 *
 * Responsibilities:
 * - Render the `Analytics` component from `@vercel/analytics/react`, which
 *   injects the Vercel script once. The `/next` entry point depends on
 *   `next/navigation`; Reflex builds with Vite + React Router, so the generic
 *   React adapter is used and the route information comes from React Router.
 * - Send a page view with the route template (`/post/[pid]`) on every
 *   client-side navigation, with the script's own pushState tracking disabled
 *   so no page is ever counted twice.
 * - Install a `beforeSend` filter that drops excluded paths, strips or redacts
 *   query strings and honours the opt-out flag stored in localStorage.
 * - Expose a small imperative API on `window.__reflexVA` so the Python helpers
 *   in `actions.py` (`rx.call_script`) can track events, send manual page
 *   views, opt out and read the status.
 * - Report page views and events to the optional `onPageView` / `onEvent`
 *   triggers as JSON-safe payloads.
 *
 * The component renders its children untouched (it can wrap the whole app via
 * `App.extra_app_wraps`) and adds no DOM of its own.
 */
import { useEffect, useRef } from "react";
import { useLocation, useParams } from "react-router";
import { Analytics } from "@vercel/analytics/react";
import { computeRoute, pageview, track as vercelTrack } from "@vercel/analytics";

const API_KEY = "__reflexVA";
const OPT_OUT_STORAGE_KEY = "reflex-va:opt-out";
const REDACTED = "[redacted]";

/* ------------------------------------------------------------------ helpers */

const isPlainObject = (value) =>
  value !== null && typeof value === "object" && !Array.isArray(value);

/** Drop `undefined`/`null` entries so the SDK never receives empty properties. */
const compact = (object) => {
  if (!isPlainObject(object)) return undefined;
  const out = {};
  for (const [key, item] of Object.entries(object)) {
    if (item !== undefined && item !== null) out[key] = item;
  }
  return Object.keys(out).length ? out : undefined;
};

const readStorage = (key) => {
  try {
    return window.localStorage.getItem(key);
  } catch (_error) {
    return null;
  }
};

const writeStorage = (key, value) => {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch (_error) {
    /* storage unavailable (private mode, sandboxed iframe): ignore */
  }
};

/** `/admin` matches `/admin` only; `/admin/*` matches `/admin` and everything below. */
const pathIsExcluded = (path, patterns) =>
  (patterns || []).some((pattern) => {
    if (typeof pattern !== "string" || !pattern) return false;
    if (pattern.endsWith("*")) {
      const prefix = pattern.slice(0, -1);
      return path.startsWith(prefix) || path === prefix.replace(/\/$/, "");
    }
    return path === pattern;
  });

const doNotTrackEnabled = () => {
  if (typeof navigator === "undefined") return false;
  const dnt = navigator.doNotTrack || window.doNotTrack || navigator.msDoNotTrack;
  return dnt === "1" || dnt === "yes" || navigator.globalPrivacyControl === true;
};

/**
 * React Router params -> the shape `computeRoute` expects. A splat (`*`, the
 * Reflex `[...slug]` catch-all) becomes an array so the template reads
 * `/docs/[...slug]`, like a Next.js route.
 */
const routeParams = (params) => {
  if (!isPlainObject(params) || !Object.keys(params).length) return null;
  const out = {};
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    if (key === "*") out.splat = String(value).split("/").filter(Boolean);
    else out[key] = value;
  }
  return Object.keys(out).length ? out : null;
};

/**
 * Apply `includeSearch` / `redactSearchParams` to a URL string. The fragment is always
 * dropped: it is never needed for analytics and is where OAuth implicit flows and magic
 * links put tokens (`#access_token=...`).
 */
const filterUrl = (raw) => {
  let url;
  try {
    url = new URL(raw, window.location.href);
  } catch (_error) {
    return raw;
  }
  url.hash = "";
  if (!state.includeSearch) {
    url.search = "";
  } else if (state.redactSearchParams.length && url.search) {
    for (const key of state.redactSearchParams) {
      if (url.searchParams.has(key)) url.searchParams.set(key, REDACTED);
    }
  }
  return url.href;
};

/* ------------------------------------------------- the shared browser state */

const state = {
  injected: false,
  disabled: false,
  disabledReason: null,
  mode: null,
  includeSearch: true,
  redactSearchParams: [],
  excludePaths: [],
  lastPath: null,
  lastRoute: null,
  listeners: new Set(),
};

const notify = (payload) => {
  const entry = { ...payload, timestamp: new Date().toISOString() };
  state.listeners.forEach((listener) => {
    try {
      listener(entry);
    } catch (error) {
      console.error("reflex-vercel-analytics: onEvent listener failed", error);
    }
  });
};

const isOptedOut = () => readStorage(OPT_OUT_STORAGE_KEY) === "1";

const pathnameOf = (raw) => {
  try {
    return new URL(raw, window.location.href).pathname;
  } catch (_error) {
    return "";
  }
};

/** True when the filter would veto an event for this URL (opt-out or excluded route). */
const wouldDrop = (raw) => isOptedOut() || pathIsExcluded(pathnameOf(raw), state.excludePaths);

/**
 * `beforeSend` handed to the SDK. It sees every page view and custom event the
 * script is about to send (`{type, url}`), after the queue is drained, so it is
 * the one place that can veto events queued before the filter settings were
 * known and the script's own page views when `trackPageViews` is off.
 */
const beforeSend = (event) => {
  if (!event || wouldDrop(event.url)) return null;
  return { ...event, url: filterUrl(event.url) };
};

const currentPath = () => window.location.pathname + window.location.search + window.location.hash;

/** `src` of the script the SDK injected (tagged with `data-sdkn`), or null before injection. */
const injectedScriptSrc = () => {
  if (typeof document === "undefined") return null;
  const script = document.head.querySelector('script[data-sdkn^="@vercel/analytics"]');
  return script ? script.getAttribute("src") : null;
};

const api = {
  /** Custom event: `track("Signup", {method: "email"}, flags)`. */
  track: (name, properties, flags) => {
    if (state.disabled) return false;
    const data = compact(properties);
    const options = flags ? { flags } : undefined;
    vercelTrack(name, data, options);
    const url = window.location.href;
    notify({ source: "python", type: "event", name, data: data ?? null, url: filterUrl(url), dropped: wouldDrop(url) });
    return true;
  },

  /** Manual page view. `path` defaults to the current location, `route` to `path`. */
  pageView: (path, route) => {
    if (state.disabled) return false;
    const finalPath = path || currentPath();
    const finalRoute = route || pathnameOf(finalPath);
    pageview({ route: finalRoute, path: finalPath });
    state.lastPath = finalPath;
    state.lastRoute = finalRoute;
    notify({
      source: "python",
      type: "pageview",
      path: finalPath,
      route: finalRoute,
      url: filterUrl(finalPath),
      dropped: wouldDrop(finalPath),
    });
    return true;
  },

  /** Opt-out: remembered in localStorage, `beforeSend` then drops every event. */
  optOut: () => {
    writeStorage(OPT_OUT_STORAGE_KEY, "1");
    return true;
  },

  optIn: () => {
    writeStorage(OPT_OUT_STORAGE_KEY, null);
    return true;
  },

  isOptedOut,

  status: () => ({
    injected: state.injected,
    disabled: state.disabled,
    disabled_reason: state.disabledReason,
    mode: state.mode,
    opted_out: isOptedOut(),
    last_path: state.lastPath,
    last_route: state.lastRoute,
    script_src: injectedScriptSrc(),
  }),
};

if (typeof window !== "undefined") {
  window[API_KEY] = api;
}

/* -------------------------------------------------------------- component */

const disable = (reason) => {
  state.disabled = true;
  state.disabledReason = reason;
};

export function ReflexVercelAnalytics({
  children,
  onReady,
  onPageView,
  onEvent,
  enabled = true,
  mode,
  debug,
  trackPageViews = true,
  includeSearch = true,
  redactSearchParams,
  excludePaths,
  respectDoNotTrack = false,
  scriptSrc,
  dsn,
  eventEndpoint,
  viewEndpoint,
  sessionEndpoint,
  endpoint,
  basePath,
  configString,
  framework = "reflex",
}) {
  const location = useLocation();
  const params = useParams();
  const listenerRef = useRef(onEvent);
  listenerRef.current = onEvent;

  // Keep the filter settings reachable from `beforeSend` and the API.
  state.includeSearch = !!includeSearch;
  state.redactSearchParams = Array.isArray(redactSearchParams) ? redactSearchParams : [];
  state.excludePaths = Array.isArray(excludePaths) ? excludePaths : [];
  state.mode = mode ?? state.mode;

  // Decide once per page load whether the script may be injected at all.
  if (!state.injected && !state.disabled) {
    if (!enabled) disable("disabled");
    else if (respectDoNotTrack && doNotTrackEnabled()) disable("do_not_track");
  }
  const active = !state.disabled;

  // Event listener first, so the initial page view is reported too.
  useEffect(() => {
    const listener = (payload) => listenerRef.current?.(payload);
    state.listeners.add(listener);
    return () => state.listeners.delete(listener);
  }, []);

  useEffect(() => {
    if (active) state.injected = true;
    onReady?.(api.status());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // One page view per client-side navigation, with the route template.
  const path = location.pathname + location.search + location.hash;
  const route = computeRoute(location.pathname, routeParams(params)) ?? location.pathname;
  useEffect(() => {
    if (!active || !trackPageViews) return;
    if (path === state.lastPath) return; // StrictMode double effects, same-page rerenders
    state.lastPath = path;
    state.lastRoute = route;
    const payload = { path, route, url: filterUrl(path), dropped: wouldDrop(path) };
    notify({ source: "router", type: "pageview", ...payload });
    if (payload.dropped) return; // excluded route / opted out: nothing is queued
    pageview({ route, path: location.pathname });
    onPageView?.(payload);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, trackPageViews, active]);

  if (!active) return children ?? null;

  const analyticsProps = {
    beforeSend,
    framework,
    mode,
    debug,
    scriptSrc,
    dsn,
    eventEndpoint,
    viewEndpoint,
    sessionEndpoint,
    endpoint,
    basePath,
    configString,
  };
  for (const key of Object.keys(analyticsProps)) {
    if (analyticsProps[key] === undefined || analyticsProps[key] === null) delete analyticsProps[key];
  }
  // `route: null` turns the script's own pushState tracking off without
  // letting the Analytics component send page views itself: this bridge does.
  if (trackPageViews) analyticsProps.route = null;

  return (
    <>
      <Analytics {...analyticsProps} />
      {children ?? null}
    </>
  );
}
