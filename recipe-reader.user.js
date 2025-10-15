// ==UserScript==
// @name         Recipe Reader
// @namespace    https://github.com/j01t3d/recipe-reader
// @version      1.1
// @description  redirects to print-friendly pages of recipe sites, using statistically generated keywords
// @author       j01t3d
// @match        https://*/*
// @grant        none
// @license      MIT
// ==/UserScript==

(function() {
    'use strict';

    function isPrintPage() {
        return /(?:[?&]print=|\/print(?:\/|$)|recipe\/print|print[-_]view|printpage|wprm[-_]print)/i.test(location.href);
    }

    function isRecipePage() {
        const keywords = { /* determined by analyze_recipes.py */
            "tablespoons": 4253, "frosting": 2475, "blueberries": 1878, "yummy": 1770,
            "skinnytaste": 1720, "parchment": 1629, "minced": 1612, "plums": 1574,
            "browned": 1542, "muffin": 1440, "diced": 1432, "joyofbaking": 1422,
            "smitten": 1340, "preheat": 1247, "toppings": 1241, "paprika": 1222,
            "kosher": 1189, "crumb": 1166, "drizzle": 1159, "thyme": 1141,
            "raspberries": 1085, "bundt": 1027, "brunch": 1020, "tortillas": 1019,
            "crockpot": 959, "cornstarch": 948, "reheat": 947, "pecans": 918,
            "oregano": 911, "leite": 888, "boneless": 884, "granulated": 883,
            "cook's": 874, "garnish": 862, "appetizers": 858, "substitutions": 821,
            "potassium": 819, "unsalted": 818, "torte": 797, "puree": 795,
            "cultivatewp": 770, "ganache": 759, "refrigerate": 752, "seasonings": 747,
            "saucepan": 746, "appetizer": 738, "spatula": 733, "thinly": 717,
            "enchilada": 704, "tarts": 699, "challah": 697, "carbohydrate": 683,
            "softened": 677, "wedges": 662, "meringue": 654, "tasteofhome": 637,
            "culinaria": 634, "cutlery": 628, "casseroles": 620, "smittenkitchen": 619,
            "allrecipes": 601, "springform": 592, "sliders": 582, "enchiladas": 578,
            "akismet": 577, "skinless": 566, "cupcake": 550, "tieghan": 546,
            "unsweetened": 545, "saute": 544, "applesauce": 513, "krista": 513,
            "subbed": 511, "refrigerated": 509, "ree's": 506, "knead": 498,
            "panko": 495, "soggy": 486, "brownie": 481, "streusel": 475,
            "meatloaf": 474, "approximation": 472, "crumbled": 465, "mains": 453,
            "scone": 450, "flickr": 444, "marinara": 442, "yolks": 441,
            "gimme": 431, "cheeseburger": 426, "rsquo": 423, "thickened": 419,
            "hetal": 410, "biscotti": 403, "ifood": 400, "broiler": 400,
            "drawnarrow": 400, "boldarrow": 400, "longarrow": 400, "ecookbook": 396
        };

        const bodyText = document.body.textContent.toLowerCase();
        const escapeRegex = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp("(?<![a-z])(" + Object.keys(keywords).map(escapeRegex).join("|") + ")(?![a-z])", "gi");
        const matches = bodyText.match(regex);
        if (!matches) return false;

        let score = 0;
        for (const match of matches) score += keywords[match.toLowerCase()] || 0;
        const avgWeight = score / matches.length;
        return matches.length > 10 && avgWeight > 500;
    }

    function redirectToPrint(url) {
        sessionStorage.setItem('lastRecipeURL', location.href);
        sessionStorage.setItem('lastPrintURL', url);
        window.location.href = url;
    }

    function findAndRedirect() {
        if (isPrintPage() || !isRecipePage()) return false;

        const lastPrintURL = sessionStorage.getItem('lastPrintURL');
        if (lastPrintURL && location.href === sessionStorage.getItem('lastRecipeURL')) return false;

        const blockedSites = ["skinnyspatula.com"];
        if (blockedSites.some(s => location.hostname.includes(s))) return false;

        const printIndicators = /(print|wprm[_-]print)/i;
        const candidates = Array.from(document.querySelectorAll('a, button, div, span'))
            .filter(el => {
                const attrs = [
                    el.textContent,
                    el.getAttribute('href'),
                    el.getAttribute('onclick'),
                    el.getAttribute('aria-label'),
                    el.getAttribute('title'),
                    el.getAttribute('data-action'),
                    el.getAttribute('data-print')
                ].join(' ').toLowerCase();
                return printIndicators.test(attrs);
            });

        for (const el of candidates) {
            const href = el.getAttribute('href');
            if (href && printIndicators.test(href)) {
                redirectToPrint(new URL(href, location.href).href);
                return true;
            }

            const onclick = el.getAttribute('onclick');
            if (onclick) {
                const urlMatch = onclick.match(/(['"])(https?:\/\/.*?(?:print|wprm[_-]print).*?)\1/);
                if (urlMatch) {
                    redirectToPrint(urlMatch[2]);
                    return true;
                }
            }

            for (const val of Object.values(el.dataset)) {
                if (val && printIndicators.test(val)) {
                    try {
                        redirectToPrint(new URL(val, location.href).href);
                        return true;
                        // eslint-disable-next-line no-empty
                    } catch {}
                }
            }
        }
        return false;
    }

    function monitorGoBackButton() {
        // Find any button or link with "back" or "return" in the text or attributes
        const backButtons = Array.from(document.querySelectorAll('a, button'))
            .filter(el => {
                const txt = (el.textContent || el.getAttribute('aria-label') || '').toLowerCase();
                return /back|return|recipe|close/.test(txt);
            });

        // If we find one with an href, just let it do its thing
        for (const btn of backButtons) {
            const href = btn.getAttribute('href');
            if (href && !href.includes('print')) {
                btn.addEventListener('click', () => {
                    window.location.href = new URL(href, location.href).href;
                });
                return;
            }
        }

        // Fallback: if no href found, look for a data attribute that looks like a recipe URL
        for (const btn of backButtons) {
            for (const val of Object.values(btn.dataset)) {
                if (/recipe|post|\/[0-9]+/.test(val) && !val.includes('print')) {
                    btn.addEventListener('click', () => {
                        window.location.href = new URL(val, location.href).href;
                    });
                    return;
                }
            }
        }

        // If all else fails, fallback to the saved URL
        const lastRecipe = sessionStorage.getItem('lastRecipeURL');
        if (lastRecipe) {
            const fallback = document.createElement('button');
            fallback.textContent = '← Back to Recipe';
            fallback.style.cssText = `
                position: fixed; bottom: 10px; right: 10px;
                background: #333; color: white; border: none; padding: 8px 12px;
                border-radius: 4px; cursor: pointer; z-index: 9999;
            `;
            fallback.addEventListener('click', () => {
                sessionStorage.removeItem('lastPrintURL');
                window.location.href = lastRecipe;
            });
            document.body.appendChild(fallback);
        }
    }


    function onReady() {
        if (!isPrintPage()) {
            if (findAndRedirect()) return;
            const observer = new MutationObserver(() => {
                if (findAndRedirect()) observer.disconnect();
            });
            observer.observe(document.body, { childList: true, subtree: true });
            setTimeout(() => observer.disconnect(), 10000);
        } else {
            monitorGoBackButton();
        }
    }

    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        onReady();
    } else {
        window.addEventListener('DOMContentLoaded', onReady);
    }
})();
