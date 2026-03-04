# Universal Image-to-PDF Converter Bot

**A high-performance utility for instant, cross-platform image consolidation into professional PDF documents.**

## Why this tool?
In the era of mobile-first productivity, converting fragmented images into a single, structured PDF is a daily necessity. This bot is designed as a **"Swiss Army Knife"** for document handling, providing:
* **Native HEIC Support:** Seamlessly processes Apple's high-efficiency formats without requiring manual pre-conversion.
* **Granular UI Control:** Integrated settings for page orientation and compression quality via interactive Telegram interfaces.
* **Clean & Secure:** Automatic session purging ensures no user data is stored longer than necessary.

## Technical Highlights
* **Engine:** Built with `Pillow` and `FPDF` for precise document synthesis.
* **Input Sanitization:** Robust regex-based filename validation to prevent file-system conflicts.
* **User State Management:** State-aware processing logic for concurrent multi-user interactions.

## Tech Stack
* Python 3.x
* PyTelegramBotAPI
* pillow-heif (for iPhone photo support)
* FPDF

---
*Developed by Islam Ruzmetov | Building high-impact utility tools for modern workflows.*
