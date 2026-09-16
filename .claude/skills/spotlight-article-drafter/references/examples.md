# Spotlight style exemplars

Real short/long pairs from Reactome's Spotlight archive, with the house
conventions they demonstrate. All article text below is **verbatim** from the
Team Drive folder `Outreach/Reactome Research Spotlight Impact Story/`, quoted so
that drafts can be calibrated against what curators actually publish rather than
against a generic science-writing voice. Nothing here is invented.

Read this before drafting. When a convention below conflicts with a general
instinct about how to write a summary, follow the convention.

---

## The two forms, and why both exist

From `Spotlight selection and publication protocol` (Team Drive):

> **As of October 2025, we will be creating 2 spotlights per release.**
> A first will be used for the front page and should be short and concise
> highlighting the key findings and emphasizing the importance of Reactome
> data/tools to the findings in the paper.
> The second longer form will include additional information of interest about
> the study, its methods and findings, and will include terms aimed at search
> engine optimization. This version will be accessible via the "More" button
> next to the Spotlight on the front page.

Also from the protocol, and relevant to candidate screening:

> We should avoid the use of papers that are simply using Reactome standard
> pathway enrichment analysis without some other interesting technology or
> application.

Published on or about the 1st of the month. The managing editor updates the text
in Joomla and notifies the authors — not this skill, and not the drafter.

---

## Conventions visible across the archive

**Opening formula.** Most shorts open by placing the paper, not the biology:
"In their <Month Year> <Journal> paper, <Title>, <First author> et al. …" The
month cited is the issue month. Variants put the authors first
("<Authors> et al., in their <Month Year> <Journal> paper "<Title>", …") — both
are in use; the constant is that journal, month, and title appear in the first
sentence.

**Name Reactome's role explicitly, and place it.** Every example states what
Reactome contributed and where in the work it sat — "Reactome pathway analysis
revealed…", "The authors employ the pathway enrichment analysis platform of
human-centric Reactome to show…", "Reactome-guided analysis led to the
identification of…". A draft that merely mentions Reactome in passing is not
finished.

**Name the specific pathways.** Shorts routinely list the actual pathway names
("neutrophil degranulation and complement cascade", "ECM proteoglycans,
Collagen formation, and Integrin cell-surface interactions") rather than saying
"several immune pathways".

**Pathway links.** In the published HTML, pathway mentions become
`PathwayBrowser/#/<DB_ID>` links and the title becomes a link to the journal
article. Mark these up in the draft only where the source supplies the
identifier; never guess a Stable ID.

**PMID.** Carried in the long form, parenthetically after the title. The short
form usually omits it.

**Length.** Shorts in the archive run roughly 80-150 words; long forms roughly
350-550. The December 2025 examples below run longer — that is the current upper
bound, not a target.

**Footnotes for curator caveats.** Where a curator wants to record a
reservation about the paper's interpretation, the archive uses a `**` footnote
after the long form rather than softening the body text. See Stylianakis.

**SEO footer.** The long form may be followed by standing boilerplate about
Reactome (NIH-funded, open-source, manually curated, ELIXIR/Global Core Biodata
Resource, dual text-and-network representation). This is reused month to month —
do not rewrite it; ask for the current text.

---

## Example 1 — Stylianakis et al., May 2026, eBioMedicine

Source: `2024-05-May/Stylianakis blurbs.docx`. The cleanest labelled pair in the
archive, and the clearest use of a curator footnote.

**SHORT**

> To identify a possible molecular basis for the substantially improved outcomes
> in pneumonia patients treated with the antibiotic clarithromycin, Stylianakis
> et al., in their May 2026 eBioMedicine paper "Molecular pathways driving
> clarithromycin benefit in community-acquired pneumonia: analysis of the ACCESS
> randomised trial", analyzed gene expression patterns in blood cells from these
> patients. Reactome pathway analysis revealed an array of changes in
> immunoregulatory pathways that provides a plausible explanation for the effect
> of the drug.

**LONG**

> Addition of the macrolide clarithromycin to the antibiotic regimen used to
> treat adults hospitalized with bacterial pneumonia has recently been shown to
> substantially reduce the incidence of secondary sepsis and respiratory failure
> in these patients. To identify a possible molecular basis for this improvement,
> Stylianakis et al., in their May 2026 eBioMedicine paper "Molecular pathways
> driving clarithromycin benefit in community-acquired pneumonia: analysis of the
> ACCESS randomised trial" (PMID: 41934919), studied gene expression patterns in
> blood cells from these patients. Reactome pathway analysis indicated that
> clarithromycin treatment attenuates the IL-1 pathway and increases production
> of other monocyte-derived pro-inflammatory cytokines and chemokines. It is also
> associated with a complex change in the composition of neutrophil granule
> contents**. These differences reinforce the previous observations that
> macrolides attenuate host pro-inflammatory responses, limiting secondary sepsis
> due to immunoparalysis.
>
> ** The Reactome "neutrophil degranulation" pathway is essentially a catalog of
> the protein content of these granules, and series of one-step reactions in which
> the proteins initially localized within a cytosolic granule (input) become
> extracellular (output). The Reactome pathway does not include any steps by which
> this degranulation is mediated and potentially stimulated or inhibited, only a
> catalog of the proteins relocated when it does happen.

Note what the footnote does: it corrects a possible misreading of what the
Reactome pathway represents, without weakening the article's claim. This is the
right place for curator expertise about Reactome's own data model.

---

## Example 2 — Ringquist et al., October 2025, Nature Biomedical Engineering

Source: `2025-10-October/October 2025 Spotlight`. Shows the short being derived
from the long by compression, and the long naming the mechanism in more detail.

**SHORT**

> In their September 2025 Nature Biomedical Engineering paper, An
> immune-competent lung-on-a-chip for modelling the human severe influenza
> infection response, Ringquist et al. show the importance of including
> tissue-resident and circulating immune cells, as well as stromal cells, in lung
> organoid chips to obtain a more realistic human in vitro model system for
> studying viral respiratory infections. Human-centric Reactome pathway
> enrichment analysis employed in this study shows that genes expressed in immune
> and stromal cells, mediating immune response and extracellular matrix
> remodeling, respectively, are among the top 10% upregulated in influenza
> H1N1-infected lung organoids, amid a global transcriptional shutdown, showing
> the value this ex vivo model for studying lung infectious disease.

**LONG**

> In their Nature Biomedical Engineering paper, An immune-competent lung-on-a-chip
> for modelling the human severe influenza infection response, Ringquist et al.
> describe the development of a human lung organoid chip that for the first time
> includes, besides bronchial epithelial cells and pulmonary endothelial cells,
> lung stroma fibroblasts and a multitude of tissue-resident and circulatory
> immune cells. By scRNA-seq, influenza H1N1 infection of these lung-on-a-chip
> organoids leads to a dramatic transcriptional shutdown, with the number of
> transcribed genes per cell falling from over two thousand to less than three
> hundred. The authors employ the pathway enrichment analysis platform of
> human-centric Reactome to show that the top 10% of genes upregulated upon
> influenza H1N1 infection are involved in immune response and extracellular
> matrix remodelling pathways. This highlights the importance of including
> tissue-resident and circulating immune cells, as well as stromal cells, in lung
> organoid chips to obtain a more realistic in vitro model system for studying
> host-pathogen interactions and therapeutic side-effects in viral respiratory
> infections.

---

## Example 3 — Simões et al., December 2025, Nature

Source: `2025-12-December/December_2025_Spotlight_1…`. Shows the dated-prefix
variant, in-text pathway linking, and the current upper bound on length.

**SHORT**

> [December 1, 2025] In their November 2025 Nature study, Anti-progestin therapy
> targets hallmarks of breast cancer risk Simões et al. demonstrate that a short
> course of the progesterone receptor (PR) antagonist ulipristal acetate (UA) in
> premenopausal women with elevated inherited breast-cancer risk suppresses
> luminal progenitor activity, reduces epithelial proliferation, and lowers
> fibroglandular density. Gene set enrichment analysis of single-cell RNA-seq data
> using Reactome pathway annotations revealed cell-type specific responses:
> luminal hormone sensing (LHS) cells showed downregulation of RNA-processing
> pathways, whereas basal-myoepithelial cells and fibroblasts demonstrated
> significant upregulation of extracellular matrix (ECM)-related components.
> Proteomic analyses identified 65 UA-regulated proteins, and Reactome pathways
> mapping confirmed UA-mediated suppression of key ECM processes, including ECM
> proteoglycans, Collagen formation, and Integrin cell-surface interactions.
> Collectively, these findings highlight ECM remodeling and luminal progenitor
> suppression as central mechanisms through which UA may reduce breast-cancer risk.

In the published version the title links to the journal, and `extracellular
matrix (ECM)`, `ECM proteoglycans`, `Collagen formation` and `Integrin
cell-surface interactions` each link to `PathwayBrowser/#/<DB_ID>`.

---

## Example 4 — Torres et al., December 2025, Frontiers in Immunology

Source: `2025-12-December/December_2025_Spotligh_2…`. Shows the authors-first
opening, and how far the long form goes into method detail and figures.

**SHORT (opening)**

> In a LC-MS/MS-based proteomic study of plasma-derived extracellular vesicles
> (EVs) from patients with visceral leishmaniasis (VL) before and after treatment
> with liposomal amphotericin (LAmB), Torres et al. (2025), in their Frontiers in
> Immunology paper, "Proteomics of plasma-derived extracellular vesicles from
> human patients identifies biomarkers for monitoring visceral leishmaniasis
> therapy," identified 132 human proteins that distinguish active disease from
> cure.

**LONG — how Reactome results are reported**

> During active VL, Reactome pathway enrichment identified profound enrichment in
> innate immunity pathways: complement cascade (17 proteins, FDR=3.00E-11) and
> neutrophil degranulation (18 proteins, FDR=5.07E-5). The disease "Leishmania
> infection" pathway itself was prominently enriched (9 proteins, FDR=2.39E-3),
> validating the assay.

Protein counts and FDR values are carried into the long form where the paper
supplies them. Quote such numbers only from the paper; never estimate one.

---

## Example 5 — Wieder et al., November 2024, PLOS Computational Biology

Source: `2024-11_November/November2024-Spotlight-text`. A single-summary month
(pre-dating the two-form protocol), and the metadata a Spotlight document is
expected to carry alongside the text.

**SUMMARY**

> In PLOS Computational Biology, Wieder et al. (2024) employ the Reactome database
> and PathIntegrate, a single sample pathway analysis toolkit for multi-omics
> datasets based on summarization analyses (for example, principal component
> analysis), to translate multi-omics datasets from molecular abundance
> measurements to pathway activity scores, enabling integration of disparate types
> of omics data according to a common scale. PathIntegrate provides higher
> sensitivity at low signal levels and efficiently identifies perturbed pathways
> from multi-omics datasets in COVID-19 and chronic obstructive pulmonary disease
> (COPD).

The document also recorded: link to PubMed, link to the paper on the journal
website, link to the journal, and the corresponding author with full affiliation.
Supply these alongside the draft where they are known.

---

## The screening note pattern

Curators screen candidates in batches with a Pros/Cons note before drafting. From
`2025-11-November/Spotlight-Nov2025-triage-20251025.docx`:

> PMID 40993392, Cherkaoui et al. 2025 Reprogramming neuroblastoma by
> diet-enhanced polyamine depletion
> Nature. 2025 Oct;646(8085):707-715. doi: 10.1038/s41586-025-09564-0.
> **Pros:**
> Full Nature article.
> Significant new general biology (different cellular processes have different
> codon usage).
> Multi-omics analysis: pathway enrichment of RNA, ribosome-associated RNA,
> protein.
> Pathway enrichment of codons is novel and a discovery depends on analysis of
> Reactome pathways.
> **Cons:**
> Pathway enrichment analysis only.
> Cites Reactome collection in Molecular Signatures Database at MIT (Liberzon
> et al. 2015).

Two things to take from this. First, the editorial note this skill produces
should read like the above — terse, factual, weighing how central Reactome was.
Second, note what counts as a **Con**: enrichment-analysis-only usage, and
citing Reactome indirectly through MSigDB rather than citing Reactome itself.
Flag both when they apply.

---

## Provenance

Assembled 2026-09-16 from the Team Drive Spotlight folder. 22 of 98 files in
that folder were machine-readable at the time; the remaining 76 are Google Docs
that were not shared for direct export, so this is a sample of the archive rather
than all of it. Worth extending when more months become readable — in particular
with pairs from 2023 and early 2024, which are not represented here.
