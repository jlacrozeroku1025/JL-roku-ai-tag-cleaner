# 👻 Roku Tag Cleaner

A lightweight web tool that automates the cleaning of VAST tags for ad platforms like Google Ad Manager, BrightLine, DCM (Google Campaign Manager), and DoubleVerify.

---

## 🚀 Features

- ✅ Replaces `[timestamp]`, `[random]`, `[campaignid]`, etc. with GAM-compliant macros
- 👶 Automatically applies Kids Content flags for DCM tags (`tag_for_child_directed_treatment=1`, `tfua=1`)
- 👻 Adds ghost icon to GAM-ready tag columns for clarity
- 💡 Outputs Excel with:
  - Cleaned tags (`TAG (👻 CACHEBUSTED)`)
  - Notes on changes applied

---

## 🖥️ How to Use

1. Go to: [LIVE TOOL LINK HERE](https://your-render-url.onrender.com)
2. Upload your Innovid, BrightLine, or DCM Excel tag sheet (.xlsx)
3. (Optional) Check "Apply Kids Content Compliance"
4. Download your cleaned tag sheet

---

## 🛠️ Deployment Notes (For Admins)

This app is built in **Flask** and auto-deploys via [Render](https://render.com).

### Local Testing:
```bash
python3 app.py

