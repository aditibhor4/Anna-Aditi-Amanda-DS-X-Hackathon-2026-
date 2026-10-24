# Teria


**Rapid microbial testing, starting with cosmetics.**


Teria is a Hackachusetts 2026 project in the Healthcare & Biotech track (challenge H4). It explores a digital companion for a proposed rapid microbial test for cosmetics, combining product information, guided sampling, image-based test-card reading, care reminders, evidence summaries, and researcher-facing experiment simulations.


> **Prototype notice:** Teria is a research and demonstration prototype, not a validated diagnostic or product-safety tool. All Teria test-strip results, risk scores, community submissions, and lab experiment results are simulated. The physical test has not yet been biologically validated. Do not use this prototype to determine whether a cosmetic product is safe.


## Features


Teria is a Streamlit app with the following pages:


| Page | What it does |
|---|---|
| **Home** | Introduces Teria and summarizes the demo shelf. |
| **Scan** | Walks through product-specific sample-handling guidance, reads a test-card image, corrects color using a reference area, and displays a result. Includes sample images, image upload, and camera input. |
| **Test a product** | Starts from a label photo/text, Open Beauty Facts search, an existing demo-shelf product, or manual entry. Calculates a transparent 0–100 demo score and shows the contributing factors. |
| **My shelf** | Displays demo products, opening dates, estimated period-after-opening (PAO) dates, saved simulated results, and care reminders. |
| **Evidence** | Summarizes selected FDA cosmetic adverse-event reports and analyzes ingredient information from Open Beauty Facts when the dataset is available. |
| **Ask AI** | Provides rule-based explanations of test results, PAO dates, formula checks, and the FDA summary. |
| **Community trends** | Shows simulated, aggregated positive results among submitted tests. This is not real community data. |
| **Lab** | Demonstrates simulated test runs, sensitivity/specificity calculations, and a confusion matrix against simulated reference labels. |
| **Find a product** | Searches the Open Beauty Facts dataset by product, brand, or barcode and displays keyword-based formula checks. |
| **About** | Describes the concept, evidence, limitations, and roadmap. |


### How the demo works


1. **Choose or identify a product.** Upload a label photo or enter label text, search the Open Beauty Facts dataset, select a demo-shelf item, or type product details manually.
2. **Review product details.** The app attempts to extract information such as ingredients, PAO (period-after-opening) months, expiry month/year, batch code, barcode, size, and product type. OCR availability depends on the installed text-recognition engine. Unrecognized fields may remain unknown.
3. **Enter use and storage details.** The demo uses details such as opening date, packaging, storage location, and whether the product is used near the eyes.
4. **Run a simulated test or scan a card image.** The image reader checks whether the photo is too dark or blurry, samples a test patch, and applies a white-reference lighting correction. In **Test a product**, the strip image itself is generated from simulated risk factors.
5. **Review the output.** The app displays a simulated result and/or a 0–100 concern score, explains the score components, and provides generic guidance. These outputs are not validated estimates of actual contamination.
6. **Save and review history.** Demo results can be saved to the session's shelf. The current shelf is held in Streamlit session state, not in a persistent user database.


## Technology


- **Python**
- **Streamlit** — web application and user interface
- **pandas / NumPy** — data processing and image calculations
- **Plotly** — interactive charts
- **Pillow (PIL)** — image loading and processing
- **OCR (optional)** — `ocrmac` on macOS or `pytesseract` when Tesseract is installed
- **Data sources** — openFDA cosmetic adverse-event reports and Open Beauty Facts product/ingredient data


The current app is a single-file Streamlit prototype. It does not require a separate backend service or database to run locally.


## Getting started


### Requirements


- Python 3
- `pip`
- The project file `New _Proj.py`
- Optional dataset file: `possibly helpful data set.zip`, or a suitable beauty-products `.tsv` file


### 1. Put the files together


Place `New _Proj.py` and the optional Open Beauty Facts dataset in the same directory. The app searches its directory tree for a `.tsv` file whose filename contains `beauty`, or a `.zip` archive containing a `.tsv` file.


The dataset is optional. Without it, label parsing and demo-shelf features can still be explored, but Open Beauty Facts search, product matching, ingredient vocabulary correction, and the dataset-based analysis will be unavailable.


### 2. Install dependencies


```bash
python3 -m pip install streamlit pandas numpy plotly pillow
```


Optional label OCR:


- **macOS:** `python3 -m pip install ocrmac`
- **Other supported setups:** install Tesseract OCR and the Python package `pytesseract`:


```bash
python3 -m pip install pytesseract
```


The Tesseract executable must also be installed and available on your system `PATH`.


### 3. Run the app


```bash
python3 -m streamlit run "New _Proj.py"
```


Open the local URL printed by Streamlit in your terminal. Stop the app with `Ctrl+C`.


The file also includes a convenience launcher for running `python3 "New _Proj.py"` directly; using the Streamlit command above is the recommended explicit launch method.


## Data and methodology


### Real external data


- **openFDA cosmetic adverse-event reports:** The code contains a selected, hard-coded summary of reports and infection-related reaction mentions, described in the app as pulled on **2026-10-24**. Adverse-event reports are voluntary and unvalidated; they do not prove that a product caused a reaction or was contaminated.
- **Open Beauty Facts:** When a compatible local dataset is supplied, the app analyzes community-contributed product and ingredient records. The code notes that the referenced export is from 2019 and is mostly French-language product data. Missing ingredient records and preservatives not included in Teria's keyword list can affect the analysis.


### Simulated or heuristic components


- The demo product catalog and sample shelf
- Test-strip images generated for the “Test a product” workflow
- The 0–100 concern score and its weighting
- Result thresholds and color classifications
- Community trend submissions
- Lab experiment outcomes and reference labels
- Formula risk levels and suggested testing intervals, which are based on ingredient keyword checks rather than laboratory measurements


The photo reader performs image-processing calculations on the provided card image, but that does **not** validate the biological assay. In the product-testing workflow, the app generates a simulated strip from demo risk factors and then runs the image reader on that generated image.


## Safety and interpretation limits


- **A demo result is not a safety verdict.** The physical test chemistry, thresholds, and interpretation need laboratory validation.
- **A low score does not prove a product is safe.** A real test could miss contamination; performance across different formulas and packaging has not been established.
- **Formula checks are heuristics.** They look for water-related terms and a predefined list of recognized preservatives in the ingredient text. They do not inspect the actual product or establish microbiological risk.
- **PAO dates are estimates from label information.** The app uses the product's open-jar period-after-opening value and the entered opening date. This is separate from contamination.
- **FDA reports are not confirmed contamination cases.** They are adverse-event reports and cannot establish causation.
- **Community and lab pages are simulations.** Their figures must not be presented as real-world prevalence or validated test performance.
- **OCR can be wrong.** Review extracted label details and correct them when needed.
- **No medical diagnosis is provided.** The explanation feature is rule-based and uses fixed text; it is not a general-purpose generative AI model or a substitute for professional advice.


## Current implementation notes


- The app uses `st.session_state` for the demo shelf. Saved changes are session-based and are not a persistent account or database.
- OCR support is optional and depends on local system setup.
- Open Beauty Facts functionality depends on a compatible local `.tsv` or `.zip` dataset.
- The in-app “AI” explainer is implemented with deterministic Python rules and fixed, source-labeled text; it does not call an external AI API.


## Roadmap


The code describes the following intended direction:


1. Calibrate the assay and thresholds in a laboratory.
2. Evaluate performance using controlled, spiked samples and appropriate reference methods.
3. Pilot with relevant users, such as makeup artists and tattoo studios.
4. Review applicable regulatory requirements before any real-world safety claims or deployment.


These are planned steps, not completed validations.


## Project context


- **Event:** Hackachusetts 2026
- **Track:** Healthcare & Biotech
- **Challenge:** H4


## Disclaimer


Teria is for demonstration and research-planning purposes only. It is not a validated microbial test, medical device, or guarantee of cosmetic product safety. Do not rely on its simulated scores or results to make health or product-use decisions.



