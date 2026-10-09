"""Debug probe v2: capture the logged-in page, map sess_ids and links, test
which sess_id yields the orders view. Log prints structure only, no PII."""
import os, re, json, time
import requests
from bs4 import BeautifulSoup
import euser_renew as ER

UA = ER.USER_AGENT
hdr = {'user-agent': UA, 'origin': 'https://www.euserv.com'}
url = "https://support.euserv.com/index.iphp"

s = requests.Session()
# trusted-device cookie load (same as EUserv class) — reuse module helpers
e = ER.EUserv(ER.AccountConfig(email=os.environ["EUSERV_EMAIL"], password=os.environ["EUSERV_PASSWORD"]))
s.cookies.update(e.session.cookies)

r0 = s.get(url, headers=hdr)
m = re.search(r'sess_id["\']?\s*[:=]\s*["\']?([a-zA-Z0-9]{30,100})["\']?', r0.text) or re.search(r'sess_id=([a-zA-Z0-9]{30,100})', r0.text)
sess1 = m.group(1)
r_login = s.post(url, headers=hdr, data={'email': os.environ["EUSERV_EMAIL"], 'password': os.environ["EUSERV_PASSWORD"],
    'form_selected_language': 'en', 'Submit': 'Login', 'subaction': 'login', 'sess_id': sess1})
print("login_status:", r_login.status_code, "bytes:", len(r_login.text))
soup = BeautifulSoup(r_login.text, 'html.parser')
print("login_page_title:", soup.title.get_text(strip=True) if soup.title else "")
print("login_has_Hello:", 'Hello' in r_login.text)
need_captcha = 'captcha' in r_login.text.lower()
print("need_captcha:", need_captcha)
if need_captcha:
    for i in range(10):
        code = ER.recognize_and_calculate("https://support.euserv.com/securimage_show.php", s)
        if not code: print("ocr_fail"); break
        r_login = s.post(url, headers=hdr, data={'subaction': 'login', 'sess_id': sess1, 'captcha_code': code})
        if 'captcha' in r_login.text.lower():
            print(f"captcha retry {i+1}"); time.sleep(3); continue
        print("captcha_ok"); break
    soup = BeautifulSoup(r_login.text, 'html.parser')
    print("post_captcha_Hello:", 'Hello' in r_login.text)

open("login_response.html", "w").write(r_login.text)

# all sess_ids present in logged-in page
ids = re.findall(r'sess_id["\']?\s*[:=]\s*["\']?([a-zA-Z0-9]{30,100})', r_login.text)
from collections import Counter
print("sess_id_counts:", dict(Counter(ids).most_common(5)))

# link map (site chrome)
links = sorted(set(re.findall(r'(?:href|action)=["\']([^"\']+)["\']', r_login.text)))
print("links_total:", len(links))
interesting = [l for l in links if 'subaction' in l or 'order' in l.lower() or 'contract' in l.lower()]
print("interesting_links:", json.dumps(interesting[:20]))

# does logged-in page already contain the order table?
print("login_resp_order_tabs:", len(soup.select('[id^="kc2_order_customer_orders_tab_content_"]')))
print("login_resp_td_z1:", len(soup.select('.td-z1-sp1-kc')))

# try follow-up GETs with each distinct sess_id
for sid in list(dict.fromkeys(ids))[:3]:
    rg = s.get(url, params={'sess_id': sid}, headers=hdr)
    sg = BeautifulSoup(rg.text, 'html.parser')
    tabs = len(sg.select('[id^="kc2_order_customer_orders_tab_content_"]'))
    is_login = 'Email address or customer ID' in rg.text
    print(f"GET sid={sid[:12]}… tabs={tabs} is_login_page={is_login} bytes={len(rg.text)}")
    open(f"get_{sid[:8]}.html", "w").write(rg.text)
