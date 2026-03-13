import urllib.request as r
import urllib.error as e
try:
    url = "https://two20539-tien-phong-tt-vl-2026.onrender.com/api/v1/auth/google/callback?iss=https%3A%2F%2Faccounts.google.com&code=4%2F0AfrIepDZ_fBRUiMAeLdA9cboYbPkR7oIuMgBjPhkntam-GQnVfrXOeuvpC9DHmp-3q5jyg&scope=email+profile+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.profile+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.email+openid&authuser=1&prompt=consent"
    print(r.urlopen(url).read().decode('utf-8'))
except e.HTTPError as err:
    print(err.code, err.read().decode('utf-8'))
