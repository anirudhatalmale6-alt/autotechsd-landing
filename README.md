# Auto Tech Specialists — Landing Page

New landing page for [autotechsd.com](https://autotechsd.com) — San Diego auto repair,
collision and EV/hybrid service center.

**Live demo:** https://anirudhatalmale6-alt.github.io/autotechsd-landing/

## What's in here

```
src/     editable source — readable HTML, commented CSS, plain JS
dist/    minified production build (this is what's deployed)
build.js run `node build.js` to regenerate dist/ from src/
```

No frameworks, no build dependencies, no external requests at runtime.
Montserrat is self-hosted (37 KB variable woff2, latin subset) so the page makes
zero third-party calls.

## Verified

| | Mobile | Desktop |
|---|---|---|
| Performance | 99 | 100 |
| Accessibility | 100 | 100 |
| Best Practices | 100 | 100 |
| SEO | 100 | 100 |

- No horizontal overflow at 1280 / 1024 / 900 / 767 / 540 / 430 / 390 / 360 / **320** px
- Zero console errors or warnings
- Booking form: required-field validation, live error clearing, past dates blocked,
  success confirmation, form reset
- All in-page anchors resolve; only external link is `tel:`

## Brand

Palette and typeface are read straight off the live Astra theme so this page sits
in the same family as the rest of the site.

| Token | Value |
|---|---|
| Red | `#ce171f` |
| Red (dark) | `#930d14` |
| Ink | `#191919` |
| Ink 2 | `#313131` |
| Typeface | Montserrat 400–800 |

## Notes

The booking form is front-end only in this demo — `src/js/main.js` shows a
confirmation panel instead of posting. On the live site the submit handler points
at the existing appointments endpoint.
