# Differential Signaling Visual Analytics Dashboard

**Research use only. Not a medical device.**
This software was developed in the HEREDITARY project as a research prototype. It has not been assessed or certified under the EU Medical Device Regulation (EU) 2017/745. It must not be used to diagnose, treat, monitor or make any other decision about individual patients.

<!-- DONE -->
<!-- For demos and web applications, also show this line in the user interface:
"Research prototype of the HEREDITARY project. Not a medical device and not for clinical use. Do not enter personal or patient data." -->

## 1. Overview

| Field                       | Value                                                                                                                                                |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Name                        | differential-cell-signaling                                                                                                                          |
| Version                     | 1.0                                                                                                                                                  |
| Type                        | Demo or web application                                                                                                                              |
| Owner partner and contact   | Institute of Visual Computing (IVC), TU Graz, Department of Information Engineering, University of Padova, Gaia Tussardi, gaia.tussardi@phd.unipd.it |
| License                     | MIT, see LICENSE file                                                                                                                                |
| Repository and DOI          | currently pending                                                                                                                                    |
| Release date                | 01-06-2026                                                                                                                                           |
| Related task or deliverable | WP5, T5.1, T5.4, D5.7, D5.1/D5.2                                                                                                                     |
| How to cite                 | pending                                                                                                                                              |

## 2. Intended use

**Primary intended use.** Exploratory analysis of differential cell signaling: which ligands,
receptors, transcription factors and cell types contribute to the differences in cellular crosstalk between a pathological and a reference condition.

**Intended users.** Biomedical researchers.

**Out-of-scope uses.** This release must not be used for

- clinical diagnosis, prognosis or treatment of individual patients;
- decisions about individuals, such as insurance, employment or access to care;
- re-identification of individuals or linkage with other data sources;
- populations, devices or data types not described in the intended use section.

## 3. Data provenance

| Dataset                                  | Source partner | Type (public, synthetic, pseudonymized, anonymized) | Population (size, age, sex, country, condition)    | Ethics approval or access conditions          |
| ---------------------------------------- | -------------- | --------------------------------------------------- | -------------------------------------------------- | --------------------------------------------- |
| ALS, snRNA-seq, Pineda et al. (2024)     | Not Applicable | public                                              | ALS patients and pathologically normal individuals | public access: doi 10.1016/j.cell.2024.02.031 |
| FMD, scRNA-seq, d'Escamard et al. (2024) | Not Applicable | public                                              | FMD murine model and wild type reference           | public access: doi 10.1038/s44161-024-00533-w |

This repository and the released files contain no personal data, pseudonymized records, identifiers or pseudonymization keys.

## 4. Method

- **Algorithm or architecture.**
- **Training setting.** Not applicable: no model is trained or shipped.
- **Privacy techniques.** None: no personal data is processed.

## 5. Performance

Not applicable: no model is trained or shipped. The dashboard is a research prototype for visual analytics of differential cell signaling data modeled as a multi-layer network.

## 6. Known limitations and risks

- **Generalizability.** The system provides a visual analytics framework for the exploration of differential cell signaling data. The results are dependent on the quality and characteristics of the input data, which may vary across populations, sites or devices. The generalizability of molecular mechanisms identified should be assessed with dedicated experimental studies.
- **Known biases and confounders.** This research approach is subject to confirmation bias, users shall be aware of this when interpreting the results. All data are from public sources and may be subject to biases in the original studies. Results are computationally inferred and may be affected by the limitations of the underlying methods, as a consequence they are not validated biomedical mechanisms but hypotheses.
- **Failure modes.** Not applicable.
- **Privacy risks.** No personal data is processed and no model is trained, so no privacy guarantee is claimed or needed.

## 7. Responsible use and reporting

- **Terms of use.** MIT license, see LICENSE file.
- **Contact for misuse or vulnerability reports.** gaia.tussardi@phd.unipd.it

## 8. Acknowledgement

Funded by the European Union under grant agreement No 101137074 (HEREDITARY). Views and opinions expressed are however those of the author(s) only and do not necessarily reflect those of the European Union or the European Health and Digital Executive Agency (HaDEA). Neither the European Union nor the granting authority can be held responsible for them.
