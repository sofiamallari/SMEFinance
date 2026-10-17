# SMEFinance

SME Finance Copilot ("Shifu") for the Shenzhen International FinTechathon (International Track, Topic E: SME Finance Copilot).

The application is in [sme-finance-copilot](sme-finance-copilot). Start with [its README](sme-finance-copilot/README.md) for setup, modules and documentation.

## Run locally

Requires Python 3.12.

```bash
git clone https://github.com/sofiamallari/SMEFinance.git
cd SMEFinance/sme-finance-copilot
python -m pip install -r requirements.txt
python -m copilot.server --host 127.0.0.1 --port 8000
```

Then open http://127.0.0.1:8000/login. A fresh clone must seed the synthetic CNY dataset first: follow [local setup](sme-finance-copilot/docs/operations/local-setup.md).

## Test

```bash
cd sme-finance-copilot
python -m unittest discover -s tests -v
```

Financial data is synthetic (CNY) and payments are sandbox-only. No real payments, credit decisions or production certification are implied.
