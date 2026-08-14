from playwright.sync_api import sync_playwright
URL="https://anirudhatalmale6-alt.github.io/autotechsd-landing/"
errs=[]; failed=[]
with sync_playwright() as p:
    b=p.chromium.launch()
    pg=b.new_page(viewport={"width":1280,"height":800})
    pg.on("console", lambda m: errs.append((m.type,m.text)) if m.type in ("error","warning") else None)
    pg.on("pageerror", lambda e: errs.append(("pageerror",str(e))))
    pg.on("response", lambda r: failed.append((r.status, r.url)) if r.status>=400 else None)
    pg.goto(URL, wait_until="networkidle"); pg.wait_for_timeout(1500)
    print("title:", pg.title())
    print("images loaded:", pg.evaluate("Array.from(document.images).every(i=>i.complete && i.naturalWidth>0)"),
          "/", pg.evaluate("document.images.length"))
    print("font applied:", pg.evaluate("getComputedStyle(document.querySelector('h1')).fontFamily"))
    pg.fill("#f-name","Test Client"); pg.fill("#f-phone","8585550134"); pg.fill("#f-email","t@example.com")
    pg.select_option("#f-service","Collision & auto body")
    pg.click("#book button[type=submit]"); pg.wait_for_timeout(700)
    print("form success on live:", not pg.eval_on_selector("#formOk","e=>e.hidden"))
    pg.screenshot(path="qa/live-desktop.png")
    m=b.new_page(viewport={"width":390,"height":780}, is_mobile=True, has_touch=True)
    m.goto(URL, wait_until="networkidle"); m.wait_for_timeout(1200)
    m.screenshot(path="qa/live-mobile.png")
    b.close()
print("HTTP >=400:", failed or "none")
print("console:", errs or "none")
