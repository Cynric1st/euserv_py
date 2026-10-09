"""Probe v3: faithful e.login() with response interception; then try multiple
panel-entry variants. Structure-only output; pages go to artifact."""
import os, re, json, time
import euser_renew as ER
from bs4 import BeautifulSoup

cfg = ER.AccountConfig(email=os.environ["EUSERV_EMAIL"], password=os.environ["EUSERV_PASSWORD"])
e = ER.EUserv(cfg)

orig_post = e.session.post
captured = []
def wrapped(*a, **k):
    r = orig_post(*a, **k)
    captured.append(r)
    return r
e.session.post = wrapped

ok = e.login()
print("login_ok:", ok)
for i, r in enumerate(captured):
    print(f"post{i}: status={r.status_code} bytes={len(r.text)} url={r.url[:80]}")
    hist = [(h.status_code, h.headers.get('Location','')[:60]) for h in r.history]
    if hist: print(f"  redirects: {hist}")
    if r.status_code and len(r.text) > 100:
        open(f"login_post{i}.html", "w").write(r.text)
        ids = re.findall(r'sess_id["\']?\s*[:=]\s*["\']?([a-zA-Z0-9]{30,100})', r.text)
        from collections import Counter
        print(f"  sess_ids: {dict(Counter(x[:10] for x in ids).most_common(4))}")
        soup = BeautifulSoup(r.text, 'html.parser')
        print(f"  Hello={('Hello' in r.text)} tabs={len(soup.select('[id^=\"kc2_order_customer_orders_tab_content_\"]'))} td_z1={len(soup.select('.td-z1-sp1-kc'))}")

print("cookies:", [f"{c.name}@{c.domain}" for c in e.session.cookies])

hdr = {'user-agent': ER.USER_AGENT, 'origin': 'https://www.euserv.com'}
if ok:
    # variant A: classic GET sess_id
    rA = e.session.get("https://support.euserv.com/index.iphp", params={'sess_id': e.sess_id}, headers=hdr)
    print(f"GET_sess_id: {rA.status_code} bytes={len(rA.text)} login_page={'Email address or customer ID' in rA.text}")
    open("varA.html","w").write(rA.text)
    # variant B: bare GET (cookie-only)
    rB = e.session.get("https://support.euserv.com/index.iphp", headers=hdr)
    print(f"GET_bare: {rB.status_code} bytes={len(rB.text)} login_page={'Email address or customer ID' in rB.text}")
    open("varB.html","w").write(rB.text)
    # variant C/D: POST navigation with subaction guesses
    for sub in ["main", "orders", "customer_orders", "show_orders"]:
        rC = e.session.post("https://support.euserv.com/index.iphp", headers=hdr,
                            data={'sess_id': e.sess_id, 'subaction': sub})
        is_login = 'Email address or customer ID' in rC.text
        soup = BeautifulSoup(rC.text, 'html.parser')
        tabs = len(soup.select('[id^="kc2_order_customer_orders_tab_content_"]'))
        print(f"POST sub={sub}: {rC.status_code} bytes={len(rC.text)} login_page={is_login} tabs={tabs}")
        if tabs or (not is_login and len(rC.text)>1000):
            open(f"varC_{sub}.html","w").write(rC.text)
