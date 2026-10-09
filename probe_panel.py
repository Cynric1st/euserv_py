"""Debug probe (branch-only): login with secrets, dump orders-page structure.
Prints only element COUNTS and site-chrome ids to the log; full HTML goes to
an admin-only artifact. Never prints credentials or server IDs."""
import os, sys, json
from euser_renew import AccountConfig, EUserv
import euser_renew

cfg = AccountConfig(email=os.environ["EUSERV_EMAIL"], password=os.environ["EUSERV_PASSWORD"])
e = EUserv(cfg)
ok = False
for i in range(6):
    if e.login():
        ok = True
        print("LOGIN_OK")
        break
    print(f"attempt {i+1} failed")
    import time; time.sleep(20)
if not ok:
    print("LOGIN_FAILED"); sys.exit(1)

from bs4 import BeautifulSoup
r = e.session.get(url=f"https://support.euserv.com/index.iphp?sess_id={e.sess_id}",
                  headers={'user-agent': getattr(euser_renew, 'USER_AGENT', 'Mozilla/5.0'),
                           'origin': 'https://www.euserv.com'})
open("orders_page.html", "w").write(r.text)
soup = BeautifulSoup(r.text, 'html.parser')
summary = {
    "http_status": r.status_code,
    "page_bytes": len(r.text),
    "title": soup.title.get_text(strip=True) if soup.title else "",
    "tabs_kc2_order_customer_orders": len(soup.select('[id^="kc2_order_customer_orders_tab_content_"]')),
    "kc2_order_table_rows": len(soup.select('.kc2_order_table tr')),
    "kc2_content_table_rows": len(soup.select('.kc2_content_table tr')),
    "td_z1_sp1_kc_cells": len(soup.select('.td-z1-sp1-kc')),
    "td_z1_sp2_kc_cells": len(soup.select('.td-z1-sp2-kc')),
    "kc2_class_elements_total": len(soup.select('[class*="kc2"]')),
    "divs_total": len(soup.find_all("div")),
    "tables_total": len(soup.find_all("table")),
}
# structure ids (site chrome only — kc2_/order ids, no data)
summary["structure_ids"] = sorted({x.get("id") for x in soup.select("[id]")
    if x.get("id") and ("kc2" in x.get("id") or "order" in x.get("id").lower())})[:40]
# classes present on table rows (chrome)
summary["row_class_samples"] = sorted({" ".join(x.get("class", [])) for x in soup.find_all("tr")})[:30]
print(json.dumps(summary, ensure_ascii=False, indent=1))
