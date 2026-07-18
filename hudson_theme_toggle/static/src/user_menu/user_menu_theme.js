import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";

// Function to apply theme to an iframe document
export function applyThemeToIframe(iframe) {
    try {
        if (!iframe || !iframe.contentDocument || !iframe.contentDocument.documentElement) {
            return;
        }
        const isDark = document.documentElement.classList.contains("o_dark_mode");
        if (isDark) {
            iframe.contentDocument.documentElement.classList.add("o_dark_mode");
        } else {
            iframe.contentDocument.documentElement.classList.remove("o_dark_mode");
        }
    } catch (e) {
        // Suppress cross-origin warnings silently
    }
}

// Function to apply theme to all visible iframes
export function applyThemeToAllIframes() {
    const iframes = document.querySelectorAll("iframe");
    iframes.forEach(applyThemeToIframe);
}

// Set up a MutationObserver to apply the theme class to dynamically loaded iframes
const iframeObserver = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
            if (node.tagName === "IFRAME") {
                node.addEventListener("load", () => applyThemeToIframe(node));
                applyThemeToIframe(node);
            } else if (node.querySelectorAll) {
                const iframes = node.querySelectorAll("iframe");
                iframes.forEach((iframe) => {
                    iframe.addEventListener("load", () => applyThemeToIframe(iframe));
                    applyThemeToIframe(iframe);
                });
            }
        });
    });
});

// Run observer when document is ready
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
        iframeObserver.observe(document.documentElement, { childList: true, subtree: true });
        applyThemeToAllIframes();
    });
} else {
    iframeObserver.observe(document.documentElement, { childList: true, subtree: true });
    applyThemeToAllIframes();
}

// Periodic check fallback to catch any state transitions or missed events
setInterval(applyThemeToAllIframes, 1000);

export function themeToggleItem(env) {
    const isDark = document.documentElement.classList.contains("o_dark_mode");

    return {
        type: "switch",
        id: "hudson_dark_mode",
        description: _t("Dark Mode"),
        isChecked: isDark,
        callback: async function () {
            const nextState = !document.documentElement.classList.contains("o_dark_mode");
            
            // Apply client-side immediately
            if (nextState) {
                document.documentElement.classList.add("o_dark_mode");
                document.cookie = "hudson_dark_mode=true; path=/; max-age=31536000";
            } else {
                document.documentElement.classList.remove("o_dark_mode");
                document.cookie = "hudson_dark_mode=false; path=/; max-age=31536000";
            }

            // Immediately apply to any open iframe views
            applyThemeToAllIframes();

            // Sync with backend model (res.users)
            try {
                await env.services.orm.write("res.users", [user.userId], {
                    dark_mode: nextState
                });
            } catch (err) {
                console.error("Failed to save dark mode preference", err);
            }
        },
        sequence: 45, // Places it just above 'My Preferences' (sequence 50)
    };
}

// Synchronize session info state with cookie & document class on JS load
if (session.hudson_dark_mode) {
    document.documentElement.classList.add("o_dark_mode");
    document.cookie = "hudson_dark_mode=true; path=/; max-age=31536000";
} else if (session.hudson_dark_mode === false) {
    document.documentElement.classList.remove("o_dark_mode");
    document.cookie = "hudson_dark_mode=false; path=/; max-age=31536000";
}

registry.category("user_menuitems").add("hudson_dark_mode", themeToggleItem);
