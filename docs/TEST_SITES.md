# PhishGuard Test Sites

Use these URLs to verify the extension's classification logic.

## 🟢 Safe Sites (Green Badge)
These sites are in the `SAFE_DATASET` (Allowlist). They should always appear as **Safe**.

-   [Google](https://www.google.com)
-   [GitHub](https://github.com)
-   [Railway](https://railway.com)
-   [Drive](https://drive.google.com)
-   [PayPal](https://www.paypal.com) (Real site)

## 🔴 Malicious Sites (Red Badge)
These sites are in the `MALICIOUS_DATASET` (Blocklist). They should always appear as **Malicious**.

-   `https://purplehoodie.com`
-   `https://apunkagames.net`
-   `https://sadeempc.com`
-   `https://crackingpatching.com`
-   `https://oceanofgames.com`

## 🟠 Suspicious Sites (Orange Badge)
These URLs trigger specific **Heuristic Checks** in our code.

| Trigger | Test URL (Copy & Paste) | Why? |
| :--- | :--- | :--- |
| **Brand Misuse** | `http://paypal-secure-update.com` | Contains "paypal" but is not `paypal.com` |
| **Brand Misuse** | `http://google-login-verify.net` | Contains "google" but is not `google.com` |
| **Risky TLD** | `http://example-test.xyz` | Ends in `.xyz` (Risky TLD) |
| **Risky TLD** | `http://bank-login.tk` | Ends in `.tk` (Risky TLD) |
| **IP Address** | `http://192.168.1.1` | Hostname is an IP address |
| **Keywords** | `http://example.com/login-secure-update` | contains "login", "secure", "update" |
| **@ Symbol** | `http://user:pass@example.com` | Contains `@` (Auth bypass attempt) |
| **Not HTTPS** | `http://example.com` | Plain HTTP |

> **Note:** Some of these might not resolve to a real page, but the extension will still analyze the URL in the address bar.

## ⚪ Unknown Sites (Grey Badge)
These sites are **Safe** but **Not in our Allowlist**. They should appear as "Unknown".
(Unless the ML model flags them as suspicious remotely).

> **Note:** Our ML model prefers `www.` subdomains. Use the full URLs below.

-   `https://www.rust-lang.org`
-   `https://www.etherscan.io`
-   `https://www.neocities.org`
-   `https://www.projecteuler.net`
-   `https://www.lichess.org`
-   `https://www.example.com`
