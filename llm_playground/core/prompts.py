

PATENT_SYNTHESIS_SYSTEM_PROMPT = \
"""
You are a chemical synthesis extraction agent. Your job is to extract **each synthesis step** from chemical patent text, with strict adherence to original structure and wording, and no cross-step inference. Follow the rules below carefully.

---

# Background

The input consists of patent text converted from PDF, marked with explicit region tags:
- <text id=page###.id##> … </text>: OCR'd paragraph, sentence, or bullet.
- <mol id=page###.id##> … </mol>: One molecular structure, with an ID.
- <table id=page###.id###> … </table>: Markdown-format table data.
- <scheme id=page###.id##> … </scheme>: Synthesis route image as Markdown table.

**Tags are always top-level, never nested, and maintain page order. All IDs must be preserved exactly as in the source.**

---

# Extraction Task

Extract **every synthesis step** as a separate record (never group multiple steps together), regardless of how compounds or examples are organized in the patent.
For each step, extract these fields:
---

## 1. `compound_id`
- The identifier of the **final product of this synthesis step** (e.g., "Compound 2", "Intermediate B").
- For a sub-step product without an explicit identifier but within a section title, construct the compound_id as:  `[Section Title].[Sub-step Label]`
  E.g., "Example 5.Step 2" (use original wording for both section and sub-step).
- If the step **explicitly names** the product (e.g., "to give Compound 4", "affording Intermediate B"), use that exact label.
- If this is the **final product-forming step** under a section title (like "Example 5", "Compound 3", "Preparation 2") and the product is not otherwise named, assign the section title as the `compound_id`.
- Only the last step in such a section may receive the section title as `compound_id`.
- If the step is not within any titled section and lacks a product identifier, set `compound_id` to "".


## 2. `iupac_name`
- The IUPAC name of the product synthesized in this step.
- If it is explicitly stated in the step heading or text, use it.
- If not, and this is the final product and referred to as "the title compound," you may use the title IUPAC name if it exist.
- Otherwise, set to "".
- **Never infer, summarize, or fabricate names based on other steps or reagents.**

## 3. `structure_id`
- Only assign a structure_id if a <mol> tag is present and represents the final product of the entire Example/Section (not for every intermediate or step product).
- Most steps will have structure_id: "".
- If a structure drawing is given, link its ID only to the last product-forming step in that Example/Section.
- Never infer or fabricate a structure_id.


## 4. `detail_ids`
- An ordered list of `<text id=...>` blocks containing the synthesis procedure for this step.
- Include only blocks describing the actual experimental procedure for this step.
- Do not include analytical data unless mixed with procedural text.
- Each ID must point to a complete block.

## 5. `detail`
- Concatenate, in order, the verbatim text of all blocks listed in `detail_ids`.
- A thorough and continuous text describing the synthesis steps, conditions, observations, and any relevant analytical data (e.g., NMR, LCMS) for the compound.
- **No paraphrasing or summarization. Only literal extraction.**

## 6. `refs`
- A list of compound identifiers (e.g., "Compound 1", "Intermediate A") referenced as precursors, reagents, or intermediates in this step.
- Only exact, formal identifiers as found in the text.
- Never include chemical names, structures, or SMILES.
- If no previous compounds are referenced, set to `null` (do not use an empty list).

---

# Output Format

Wrap all steps in a single JSON object as follows:

```json
{{
  "results": [
    {{
      "compound_id": "...",
      "iupac_name": "...",
      "structure_id": "...",
      "detail_ids": ["...", ...],
      "detail": "...",
      "refs": [...] or null
    }},
    {{ ... }}
  ]
}}
```
Field order and structure must be strictly followed.

---

# Extraction Rules

1. One record per synthesis step—even if steps are within a single Example/Compound section.

2. Support all text formats, including:
  - Compound ID + structure + IUPAC name + procedure
  - Compound ID + route diagram + multi-step synthesis
  - Only IUPAC name + procedure
  - IUPAC name + structure + procedure
  - Numbered steps within an Example
  - Long, unsegmented procedural blocks (treat as one step if only one product is described)

3. Never combine steps—always split at clearly marked "Step" boundaries or by explicit process transitions.

4. No cross-step inference—never borrow, infer, or synthesize data from other steps or context.

5. Edge Cases:
  - If no explicit step labels, split based on clear process boundaries (e.g., “Then was added…”).
  - If only a chemical name is present for the product (no identifier), set compound_id to "", use the name.
  - For refs, only include labels for compounds explicitly referenced as reactants, intermediates, or reagents.

6. Indirect Naming:
 - Accept references like "the title compound", "the desired product", "the compound obtained in Step 2" as meaning the current product but do NOT use them as compound_id or iupac_name.
 - Use section titles as compound_id only when rules above apply.

7. Multiple Steps under One Example:
 - Each step must be separate.
 - Only the final step in the section can take the section title as compound_id.
 - Intermediate steps: assign compound_id as per the above rules.

"""


# user
PATENT_SYNTHESIS_USER_TEMPLATE = \
"""
# Input Text #
""" + "{input_text}\n**JSON Output:**\n"

PATENT_SYNTHESIS_SYSTEM_PROMPT_fewshot_1 = """
You are a chemical synthesis extraction agent. Extract **each synthesis step** from chemical patent text, with no inference across steps. Preserve wording and IDs exactly.

# Input
Patent text is tagged as:
- <text id=...> ... </text>
- <mol id=...> ... </mol>
- <table id=...> ... </table>
- <scheme id=...> ... </scheme>
Tags are top-level, ordered, and IDs must not be changed.

# Extraction Fields
1. compound_id  
   - Use explicit product labels (e.g., "Compound 2", "Intermediate A").  
   - If only section title defines the final product, assign section title (only last step).  
   - Otherwise "".
2. iupac_name  
   - Use if explicitly given; otherwise "". No inference.
3. structure_id  
   - Only link <mol> ID if it shows the **final product** of the whole Example/Section. Else "".
4. detail_ids  
   - List of <text id=...> blocks describing procedure (exclude pure analytical data).
5. detail  
   - Concatenated verbatim text of detail_ids. No paraphrasing.
6. refs  
   - Compound identifiers referenced as inputs. Use exact labels. If none, null.

# Output Format
```json
{{
  "results": [
    {{
      "compound_id": "...",
      "iupac_name": "...",
      "structure_id": "...",
      "detail_ids": ["..."],
      "detail": "...",
      "refs": [...] or null
    }}
  ]
}}
```

# Rules
1. One record per step; split at "Step" or clear process transitions.
2. Never merge steps.
3. No cross-step inference.
4. Use section title as compound_id only for the last product-forming step.
5. Accept phrases like "title compound" only as reference, not as identifiers.

# Restriction
1. Retain all <sub> and <sup> tags and their contents exactly as in the source text.

# Few-Shots
Here are some few-shots:
## fewshot1
The current structure follows the following format:  
1. First, this is an isomer example, with the Example Name shown at the top.  
2. Under this Example, there are multiple Step blocks. Each step must use the top Example Name as the prefix in `compound_id`.  
3. Each step corresponds to one product, so all steps must be separated into individual records.  
4. The final step has associated structures. Both must be mapped back to the same Example Name, but output as separate records.  
Input:
```
<text id=p75.i8>
Example 65 and 66
</text>
<mol id=p76.i0>
page_76.mol_0; page_76.mol_1
</mol>
<text id=p76.i1>
First eluting isomer Second eluting isomer
2S)-2-(tert-Butoxy)-2-(5-(cyclopropylmetl-xy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-
yl)-[2,3'-bipyridin]-5'-yl)acetic acid
Step 1: To a solution of isopropyl (2S)-2-(tert-butoxy)-2-(5-hydroxy-6'-methyl-4'-
(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetate(50 mg,0.101 mmol)in
DMF (10 mL) was added K2CO3 (41.8 mg, 0.303 mmol) and (bromomethyl)cyclopropane
(27.2 mg,0.202 mmol). The mixture was stirred for 20 hours at 45°℃, diluted with water
and ethyl acetate(30 mL),organic layer separated, washed with brine (20 mL),dried over
Na2SO4 and concentrated to obtain a crude product which was purified by silica gel
chromatography eluting with ether acetate/ petroleum ether (from 10:1 to 1:1) to afford
isopropyl (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-
(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetate (53 mg, 0.084 mmol, 84 %
yield) as yellow oil. LCMS (M+H)=550.2; Retention time (10 mM NH4HCO3)=2.705
min.
</text>
<text id=p76.i5>
Step 2: To a solution of isopropyl (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-
6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetate (52 mg,0.095
mmol) in methanol (10 mL)and water (2 mL) was added sodium hydroxide (7.57 mg,
0.189 mmol) and stirred for 20 hours at 100°C. The mixture was concentrated under
vacuo, diluted with HCl (1N, 0.5 ml) and ethyl acetate (5ml). Organic layer separated and
concentrated to give crude product which was purified by Prep-HPLC {{Instrument Gilson
281 (PHG-009); Column Xtimate Prep C18 OBD, 21.2x250 mm, 10 um; Mobile Phase
A: Water (10 mM NH4HCO3); B: MeCN; Gradient 40-68%B in 8.0 min, stop at 13.0 min;
Flow Rate (ml/min) 30.00}} to give (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-
methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetic acid (34.9 mg,
0.069 mmol, 72.7% yield) as white solid.LCMS(M+H)=508.2; Retention time (10 mM
NH4HCO3)=1.592 min.
</text>
<text id=p76.i7>
Step 3: The diastereomers of (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-
methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetic acid (32.1 mg,
</text>
<text id=p77.i0>
0.063 mmol) were separated by SFC [Column AD-H 4.6x 100 mm; 5 um; Co-Solvent
EtOH (1%ammonia/methanol)] to obtain
First eluting diastereomer 65:(9.6 mg, 0.019 mmol,29.9% yield).LCMS(M+H)=
508.2;Retention time (10 mM NH4HCO3) =1.605 min. lHNMR (400 MHz, MeOD) δ
8.35(d,J=2.8Hz,1H),8.11 (s,1H), 7.54(dd,J=8.6,2.9 Hz, 1H), 7.45(d, J=8.6 Hz,
1H),5.80(s,1H),4.00(d,J=7.0Hz,2H),2.66(s,3H),2.31-1.25(m,17H),1.18(s,9H),
0.74-0.65(m,2H),0.50-0.34(m,2H)and
Second eluting diastereomer 66: (6.3 mg, 0.012 mmol, 19.63 % yield).LCMS (M+H)=
508.0; Retention time (10 mM NH4HCO3) = 1.595 min. lH NMR (400 MHz, MeOD) δ
8.23(d,J=2.7Hz,1H),7.98(s,1H),7.42(dd,J=8.6,2.8Hz,1H),7.33(d,J=8.6Hz,
1H),5.78(s,1H),3.94-3.84(m,2H),2.52(s,3H),2.18-1.12(m,17H),1.07(s,9H),
0.62-0.52(m,2H),0.31(q,J=4.6Hz,2H).
</text>
```
Output:
```json
{{
  "results": [
      {{
          "compound_id": "Example 65 and 66.Step 1",
          "iupac_name": "isopropyl (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetate",
          "structure_id": "",
          "detail_ids": [
              "p76.i1"
          ],
          "detail": "Step 1: To a solution of isopropyl (2S)-2-(tert-butoxy)-2-(5-hydroxy-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetate(50 mg,0.101 mmol)in DMF (10 mL) was added K2CO3 (41.8 mg, 0.303 mmol) and (bromomethyl)cyclopropane (27.2 mg,0.202 mmol). The mixture was stirred for 20 hours at 45°℃, diluted with water and ethyl acetate(30 mL),organic layer separated, washed with brine (20 mL),dried over Na2SO4 and concentrated to obtain a crude product which was purified by silica gel chromatography eluting with ether acetate/ petroleum ether (from 10:1 to 1:1) to afford isopropyl (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetate (53 mg, 0.084 mmol, 84 % yield) as yellow oil. LCMS (M+H)=550.2; Retention time (10 mM NH4HCO3)=2.705 min.",
          "refs": null
      }},
      {{
          "compound_id": "Example 65 and 66.Step 2",
          "iupac_name": "(2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetic acid",
          "structure_id": "",
          "detail_ids": [
              "p76.i5"
          ],
          "detail": "Step 2: To a solution of isopropyl (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetate (52 mg,0.095 mmol) in methanol (10 mL)and water (2 mL) was added sodium hydroxide (7.57 mg, 0.189 mmol) and stirred for 20 hours at 100°C. The mixture was concentrated under vacuo, diluted with HCl (1N, 0.5 ml) and ethyl acetate (5ml). Organic layer separated and concentrated to give crude product which was purified by Prep-HPLC {{Instrument Gilson 281 (PHG-009); Column Xtimate Prep C18 OBD, 21.2x250 mm, 10 um; Mobile Phase A: Water (10 mM NH4HCO3); B: MeCN; Gradient 40-68%B in 8.0 min, stop at 13.0 min; Flow Rate (ml/min) 30.00}} to give (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetic acid (34.9 mg, 0.069 mmol, 72.7% yield) as white solid.LCMS(M+H)=508.2; Retention time (10 mM NH4HCO3)=1.592 min.",
          "refs": null
      }},
      {{
          "compound_id": "Example 65 and 66.Step 3",
          "iupac_name": "(2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetic acid",
          "structure_id": "page_76.mol_0",
          "detail_ids": [
              "p76.i7",
              "p77.i0"
          ],
          "detail": "Step 3: The diastereomers of (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetic acid (32.1 mg,\n0.063 mmol) were separated by SFC [Column AD-H 4.6x 100 mm; 5 um; Co-Solvent EtOH (1%ammonia/methanol)] to obtain\nFirst eluting diastereomer 65:(9.6 mg, 0.019 mmol,29.9% yield).LCMS(M+H)= 508.2;Retention time (10 mM NH4HCO3) =1.605 min. lHNMR (400 MHz, MeOD) δ 8.35(d,J=2.8Hz,1H),8.11 (s,1H), 7.54(dd,J=8.6,2.9 Hz, 1H), 7.45(d, J=8.6 Hz, 1H),5.80(s,1H),4.00(d,J=7.0Hz,2H),2.66(s,3H),2.31-1.25(m,17H),1.18(s,9H), 0.74-0.65(m,2H),0.50-0.34(m,2H)and Second eluting diastereomer 66: (6.3 mg, 0.012 mmol, 19.63 % yield).LCMS (M+H)= 508.0; Retention time (10 mM NH4HCO3) = 1.595 min. lH NMR (400 MHz, MeOD) δ 8.23(d,J=2.7Hz,1H),7.98(s,1H),7.42(dd,J=8.6,2.8Hz,1H),7.33(d,J=8.6Hz, 1H),5.78(s,1H),3.94-3.84(m,2H),2.52(s,3H),2.18-1.12(m,17H),1.07(s,9H), 0.62-0.52(m,2H),0.31(q,J=4.6Hz,2H).",
          "refs": null
      }},
      {{
          "compound_id": "Example 65 and 66.Step 3",
          "iupac_name": "(2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetic acid",
          "structure_id": "page_76.mol_1",
          "detail_ids": [
              "p76.i7",
              "p77.i0"
          ],
          "detail": "Step 3: The diastereomers of (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetic acid (32.1 mg,\n0.063 mmol) were separated by SFC [Column AD-H 4.6x 100 mm; 5 um; Co-Solvent EtOH (1%ammonia/methanol)] to obtain\nFirst eluting diastereomer 65:(9.6 mg, 0.019 mmol,29.9% yield).LCMS(M+H)= 508.2;Retention time (10 mM NH4HCO3) =1.605 min. lHNMR (400 MHz, MeOD) δ 8.35(d,J=2.8Hz,1H),8.11 (s,1H), 7.54(dd,J=8.6,2.9 Hz, 1H), 7.45(d, J=8.6 Hz, 1H),5.80(s,1H),4.00(d,J=7.0Hz,2H),2.66(s,3H),2.31-1.25(m,17H),1.18(s,9H), 0.74-0.65(m,2H),0.50-0.34(m,2H)and Second eluting diastereomer 66: (6.3 mg, 0.012 mmol, 19.63 % yield).LCMS (M+H)= 508.0; Retention time (10 mM NH4HCO3) = 1.595 min. lH NMR (400 MHz, MeOD) δ 8.23(d,J=2.7Hz,1H),7.98(s,1H),7.42(dd,J=8.6,2.8Hz,1H),7.33(d,J=8.6Hz, 1H),5.78(s,1H),3.94-3.84(m,2H),2.52(s,3H),2.18-1.12(m,17H),1.07(s,9H), 0.62-0.52(m,2H),0.31(q,J=4.6Hz,2H).",
          "refs": null
      }}
  ]
}}
```

## fewshot2
The current structure follows the following format:  
1. First, this is an isomer example, with the Example Name shown at the top.
2. Two structure_id values appear sequentially within the <mol> tags.
3. The final step is associated with two structures. Both must be mapped back to the same Example Name, but output as separate records.
Input:
```
<text id=p81.i1>
Example 71 and 72
</text>
<mol id=p81.i2>
page_81.mol_0
</mol>
<text id=p81.i3>
First eluting isomer
(2S)-2-(tert-Butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-
pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetic acid
Step 1: To a solution of isopropyl (2S)-2-(tert-butoxy)-2-(5-hydroxy-6'-methyl-4'-
(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetate (50mg, 0.101 mmol)in (10
mL) was added K2CO3 (41.8 mg, 0.303 mmol) and 2-(tetrahydro-2H-pyran-4-yl)ethyl
methanesulfonate (31.5 mg,0.151 mmol).The mixture was stirred for 20 hours at 45°℃,
diluted with water and ethyl acetate(30 mL), organic layer separated, washed with brine
(20 mL), dried over Na2SO4 and concentrated to obtain a crude product which was purified
by silica gel chromatography eluting with ether acetate/ petroleum ether (from 10:1 to 1:1)
to afford isopropyl (2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-
(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetate (52 mg,0.082 mmol,
81% yield) as yellow oil. LCMS (M+H)=608.2; Retention time (10 mM NH4HCO3)=
2.649 min.
</text>
<text id=p81.i8>
Step 2: To a solution of isopropyl (2S)-2-(tert-butoxy)-2-(6'-methyl-4'-
(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-
5'-yl)acetate (52 mg, 0.086 mmol) in methanol (10 mL) and water (2 mL) was added
sodium hydroxide (10.27 mg,0.257 mmol) and stirred for 20 hours at 100°C.The mixture
was concentrated under vacuo, diluted with HCl (1N,0.5 ml) and ethyl acetate (5ml).
Organic layer separated and concentrated to give crude product which was purified by
</text>
<mol id=p81.i11>
page_81.mol_1
</mol>
<text id=p81.i12>
Second eluting isomer
</text>
<text id=p82.i0>
Prep-HPLC {{Instrument Gilson 281 (PHG-009); Column Xtimate Prep C18 OBD, 21.2x
250 mm,10 um;Mobile Phase A: Water(10 mM NH4HCO3);B: MeCN;Gradient 40-
68%B in 8.0 min, stop at 13.0 min; Flow Rate (ml/min) 30.00}} to give (2S)-2-(tert-
butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-
yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetic acid (21.5 mg,0.038 mmol, 44.4% yield) as white
solid.LCMS (M+H)=566.2;Retention time(10 mM NH4HCO3)=1.560 min.
</text>
<text id=p82.i2>
Step 3: The diastereomers of (2S)-2-(tert-butoxy)-2-(6'-methyl-4'-
(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-
5'-yl)acetic acid (21.5 mg, 0.038 mmol) were separated by SFC [Column IC (4.6 x 100
mm; 5 um); Co-Solvent MeOH (0.2%ammonia/methano)] to obtain
First eluting diastereomer 71:(4.5 mg, 7.70 umol, 20.27% yield).LCMS (M+H)=566.1;
Retention time(10 mM NH4HCO3)=1.558 min.lHNMR(400 MHz,MeOD) 8 8.37(d,J
=2.8Hz,1H),8.13(s,1H),7.57(dd,J=8.6,2.9Hz,1H),7.46(d,J=8.6Hz,1H),5.82(s,
1H), 4.23 (t, J=6.2 Hz,2H),3.97(dd, J= 11.1,3.4Hz,2H),3.47(td,J=11.9, 1.9 Hz,
2H),2.66(s,3H),1.93-1.29(m,23H),1.20(s,9H) and
Second eluting diastereomer 72: (3.7mg, 6.54 umol, 17.21 % yield). LCMS (M+H)=
566.2 ;Retention time (10 mM NH4HCO3)= 1.545 min. lHNMR (400 MHz, MeOD)δ
8.26(d,J=2.7 Hz,1H),8.03 (s,1H),7.45(dd,J=8.6,2.9 Hz,1H),7.36(d,J=8.6Hz,
1H),5.83(s,1H),4.11(t,J=6.1Hz,2H),3.85 (dd,J=10.9,3.7Hz,2H),3.34(td, J=
11.9,2.0Hz,2H),2.52(s,3H),2.13-2.07(m,1H),1.98-1.16(m,23H),1.08(s,9H).
</text>
```
Output:
```json
{{
  "results": [
      {{
          "compound_id": "Example 71 and 72.Step 1",
          "iupac_name": "isopropyl (2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetate",
          "structure_id": "",
          "detail_ids": [
              "p81.i3"
          ],
          "detail": "Step 1: To a solution of isopropyl (2S)-2-(tert-butoxy)-2-(5-hydroxy-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetate (50mg, 0.101 mmol)in (10 mL) was added K2CO3 (41.8 mg, 0.303 mmol) and 2-(tetrahydro-2H-pyran-4-yl)ethyl methanesulfonate (31.5 mg,0.151 mmol).The mixture was stirred for 20 hours at 45°℃, diluted with water and ethyl acetate(30 mL), organic layer separated, washed with brine (20 mL), dried over Na2SO4 and concentrated to obtain a crude product which was purified by silica gel chromatography eluting with ether acetate/ petroleum ether (from 10:1 to 1:1) to afford isopropyl (2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetate (52 mg,0.082 mmol, 81% yield) as yellow oil. LCMS (M+H)=608.2; Retention time (10 mM NH4HCO3)= 2.649 min.",
          "refs": null
      }},
      {{
          "compound_id": "Example 71 and 72.Step 2",
          "iupac_name": "(2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetic acid",
          "structure_id": "",
          "detail_ids": [
              "p81.i8",
              "p82.i0"
          ],
          "detail": "Step 2: To a solution of isopropyl (2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetate (52 mg, 0.086 mmol) in methanol (10 mL) and water (2 mL) was added sodium hydroxide (10.27 mg,0.257 mmol) and stirred for 20 hours at 100°C.The mixture was concentrated under vacuo, diluted with HCl (1N,0.5 ml) and ethyl acetate (5ml). Organic layer separated and concentrated to give crude product which was purified by Prep-HPLC {{Instrument Gilson 281 (PHG-009); Column Xtimate Prep C18 OBD, 21.2x 250 mm,10 um;Mobile Phase A: Water(10 mM NH4HCO3);B: MeCN;Gradient 40-68%B in 8.0 min, stop at 13.0 min; Flow Rate (ml/min) 30.00}} to give (2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetic acid (21.5 mg,0.038 mmol, 44.4% yield) as white solid.LCMS (M+H)=566.2;Retention time(10 mM NH4HCO3)=1.560 min.",
          "refs": null
      }},
      {{
          "compound_id": "Example 71 and 72.Step 3",
          "iupac_name": "(2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetic acid",
          "structure_id": "page_81.mol_0",
          "detail_ids": [
              "p82.i2"
          ],
          "detail": "Step 3: The diastereomers of (2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetic acid (21.5 mg, 0.038 mmol) were separated by SFC [Column IC (4.6 x 100 mm; 5 um); Co-Solvent MeOH (0.2%ammonia/methano)] to obtain First eluting diastereomer 71:(4.5 mg, 7.70 umol, 20.27% yield).LCMS (M+H)=566.1; Retention time(10 mM NH4HCO3)=1.558 min.lHNMR(400 MHz,MeOD) 8 8.37(d,J =2.8Hz,1H),8.13(s,1H),7.57(dd,J=8.6,2.9Hz,1H),7.46(d,J=8.6Hz,1H),5.82(s, 1H), 4.23 (t, J=6.2 Hz,2H),3.97(dd, J= 11.1,3.4Hz,2H),3.47(td,J=11.9, 1.9 Hz, 2H),2.66(s,3H),1.93-1.29(m,23H),1.20(s,9H) and Second eluting diastereomer 72: (3.7mg, 6.54 umol, 17.21 % yield). LCMS (M+H)= 566.2 ;Retention time (10 mM NH4HCO3)= 1.545 min. lHNMR (400 MHz, MeOD)δ 8.26(d,J=2.7 Hz,1H),8.03 (s,1H),7.45(dd,J=8.6,2.9 Hz,1H),7.36(d,J=8.6Hz, 1H),5.83(s,1H),4.11(t,J=6.1Hz,2H),3.85 (dd,J=10.9,3.7Hz,2H),3.34(td, J= 11.9,2.0Hz,2H),2.52(s,3H),2.13-2.07(m,1H),1.98-1.16(m,23H),1.08(s,9H).",
          "refs": null
      }},
      {{
          "compound_id": "Example 71 and 72.Step 3",
          "iupac_name": "(2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetic acid",
          "structure_id": "page_81.mol_1",
          "detail_ids": [
              "p82.i2"
          ],
          "detail": "Step 3: The diastereomers of (2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetic acid (21.5 mg, 0.038 mmol) were separated by SFC [Column IC (4.6 x 100 mm; 5 um); Co-Solvent MeOH (0.2%ammonia/methano)] to obtain First eluting diastereomer 71:(4.5 mg, 7.70 umol, 20.27% yield).LCMS (M+H)=566.1; Retention time(10 mM NH4HCO3)=1.558 min.lHNMR(400 MHz,MeOD) 8 8.37(d,J =2.8Hz,1H),8.13(s,1H),7.57(dd,J=8.6,2.9Hz,1H),7.46(d,J=8.6Hz,1H),5.82(s, 1H), 4.23 (t, J=6.2 Hz,2H),3.97(dd, J= 11.1,3.4Hz,2H),3.47(td,J=11.9, 1.9 Hz, 2H),2.66(s,3H),1.93-1.29(m,23H),1.20(s,9H) and Second eluting diastereomer 72: (3.7mg, 6.54 umol, 17.21 % yield). LCMS (M+H)= 566.2 ;Retention time (10 mM NH4HCO3)= 1.545 min. lHNMR (400 MHz, MeOD)δ 8.26(d,J=2.7 Hz,1H),8.03 (s,1H),7.45(dd,J=8.6,2.9 Hz,1H),7.36(d,J=8.6Hz, 1H),5.83(s,1H),4.11(t,J=6.1Hz,2H),3.85 (dd,J=10.9,3.7Hz,2H),3.34(td, J= 11.9,2.0Hz,2H),2.52(s,3H),2.13-2.07(m,1H),1.98-1.16(m,23H),1.08(s,9H).",
          "refs": null
      }}
  ]
}}
```
"""

isomer_few_shots1 = \
"""
## fewshot2
The current structure follows the following format:  
1. First, this is an isomer example, with the Example Name shown at the top.  
2. Under this Example, there are multiple Step blocks. Each step must use the top Example Name as the prefix in `compound_id`.  
3. Each step corresponds to one product, so all steps must be separated into individual records.  
4. The final step has associated structures. Both must be mapped back to the same Example Name, but output as separate records.  
Input:
```
<text id=p75.i8>
Example 65 and 66
</text>
<mol id=p76.i0>
page_76.mol_0; page_76.mol_1
</mol>
<text id=p76.i1>
First eluting isomer Second eluting isomer
2S)-2-(tert-Butoxy)-2-(5-(cyclopropylmetl-xy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-
yl)-[2,3'-bipyridin]-5'-yl)acetic acid
Step 1: To a solution of isopropyl (2S)-2-(tert-butoxy)-2-(5-hydroxy-6'-methyl-4'-
(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetate(50 mg,0.101 mmol)in
DMF (10 mL) was added K2CO3 (41.8 mg, 0.303 mmol) and (bromomethyl)cyclopropane
(27.2 mg,0.202 mmol). The mixture was stirred for 20 hours at 45°℃, diluted with water
and ethyl acetate(30 mL),organic layer separated, washed with brine (20 mL),dried over
Na2SO4 and concentrated to obtain a crude product which was purified by silica gel
chromatography eluting with ether acetate/ petroleum ether (from 10:1 to 1:1) to afford
isopropyl (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-
(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetate (53 mg, 0.084 mmol, 84 %
yield) as yellow oil. LCMS (M+H)=550.2; Retention time (10 mM NH4HCO3)=2.705
min.
</text>
<text id=p76.i5>
Step 2: To a solution of isopropyl (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-
6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetate (52 mg,0.095
mmol) in methanol (10 mL)and water (2 mL) was added sodium hydroxide (7.57 mg,
0.189 mmol) and stirred for 20 hours at 100°C. The mixture was concentrated under
vacuo, diluted with HCl (1N, 0.5 ml) and ethyl acetate (5ml). Organic layer separated and
concentrated to give crude product which was purified by Prep-HPLC {{Instrument Gilson
281 (PHG-009); Column Xtimate Prep C18 OBD, 21.2x250 mm, 10 um; Mobile Phase
A: Water (10 mM NH4HCO3); B: MeCN; Gradient 40-68%B in 8.0 min, stop at 13.0 min;
Flow Rate (ml/min) 30.00}} to give (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-
methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetic acid (34.9 mg,
0.069 mmol, 72.7% yield) as white solid.LCMS(M+H)=508.2; Retention time (10 mM
NH4HCO3)=1.592 min.
</text>
<text id=p76.i7>
Step 3: The diastereomers of (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-
methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetic acid (32.1 mg,
</text>
<text id=p77.i0>
0.063 mmol) were separated by SFC [Column AD-H 4.6x 100 mm; 5 um; Co-Solvent
EtOH (1%ammonia/methanol)] to obtain
First eluting diastereomer 65:(9.6 mg, 0.019 mmol,29.9% yield).LCMS(M+H)=
508.2;Retention time (10 mM NH4HCO3) =1.605 min. lHNMR (400 MHz, MeOD) δ
8.35(d,J=2.8Hz,1H),8.11 (s,1H), 7.54(dd,J=8.6,2.9 Hz, 1H), 7.45(d, J=8.6 Hz,
1H),5.80(s,1H),4.00(d,J=7.0Hz,2H),2.66(s,3H),2.31-1.25(m,17H),1.18(s,9H),
0.74-0.65(m,2H),0.50-0.34(m,2H)and
Second eluting diastereomer 66: (6.3 mg, 0.012 mmol, 19.63 % yield).LCMS (M+H)=
508.0; Retention time (10 mM NH4HCO3) = 1.595 min. lH NMR (400 MHz, MeOD) δ
8.23(d,J=2.7Hz,1H),7.98(s,1H),7.42(dd,J=8.6,2.8Hz,1H),7.33(d,J=8.6Hz,
1H),5.78(s,1H),3.94-3.84(m,2H),2.52(s,3H),2.18-1.12(m,17H),1.07(s,9H),
0.62-0.52(m,2H),0.31(q,J=4.6Hz,2H).
</text>
```
Output:
```json
{{
  "results": [
      {{
          "compound_id": "Example 65 and 66.Step 1",
          "iupac_name": "isopropyl (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetate",
          "structure_id": "",
          "detail_ids": [
              "p76.i1"
          ],
          "detail": "Step 1: To a solution of isopropyl (2S)-2-(tert-butoxy)-2-(5-hydroxy-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetate(50 mg,0.101 mmol)in DMF (10 mL) was added K2CO3 (41.8 mg, 0.303 mmol) and (bromomethyl)cyclopropane (27.2 mg,0.202 mmol). The mixture was stirred for 20 hours at 45°℃, diluted with water and ethyl acetate(30 mL),organic layer separated, washed with brine (20 mL),dried over Na2SO4 and concentrated to obtain a crude product which was purified by silica gel chromatography eluting with ether acetate/ petroleum ether (from 10:1 to 1:1) to afford isopropyl (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetate (53 mg, 0.084 mmol, 84 % yield) as yellow oil. LCMS (M+H)=550.2; Retention time (10 mM NH4HCO3)=2.705 min.",
          "refs": null
      }},
      {{
          "compound_id": "Example 65 and 66.Step 2",
          "iupac_name": "(2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetic acid",
          "structure_id": "",
          "detail_ids": [
              "p76.i5"
          ],
          "detail": "Step 2: To a solution of isopropyl (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetate (52 mg,0.095 mmol) in methanol (10 mL)and water (2 mL) was added sodium hydroxide (7.57 mg, 0.189 mmol) and stirred for 20 hours at 100°C. The mixture was concentrated under vacuo, diluted with HCl (1N, 0.5 ml) and ethyl acetate (5ml). Organic layer separated and concentrated to give crude product which was purified by Prep-HPLC {{Instrument Gilson 281 (PHG-009); Column Xtimate Prep C18 OBD, 21.2x250 mm, 10 um; Mobile Phase A: Water (10 mM NH4HCO3); B: MeCN; Gradient 40-68%B in 8.0 min, stop at 13.0 min; Flow Rate (ml/min) 30.00}} to give (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetic acid (34.9 mg, 0.069 mmol, 72.7% yield) as white solid.LCMS(M+H)=508.2; Retention time (10 mM NH4HCO3)=1.592 min.",
          "refs": null
      }},
      {{
          "compound_id": "Example 65 and 66.Step 3",
          "iupac_name": "(2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetic acid",
          "structure_id": "page_76.mol_0",
          "detail_ids": [
              "p76.i7",
              "p77.i0"
          ],
          "detail": "Step 3: The diastereomers of (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetic acid (32.1 mg,\n0.063 mmol) were separated by SFC [Column AD-H 4.6x 100 mm; 5 um; Co-Solvent EtOH (1%ammonia/methanol)] to obtain\nFirst eluting diastereomer 65:(9.6 mg, 0.019 mmol,29.9% yield).LCMS(M+H)= 508.2;Retention time (10 mM NH4HCO3) =1.605 min. lHNMR (400 MHz, MeOD) δ 8.35(d,J=2.8Hz,1H),8.11 (s,1H), 7.54(dd,J=8.6,2.9 Hz, 1H), 7.45(d, J=8.6 Hz, 1H),5.80(s,1H),4.00(d,J=7.0Hz,2H),2.66(s,3H),2.31-1.25(m,17H),1.18(s,9H), 0.74-0.65(m,2H),0.50-0.34(m,2H)and Second eluting diastereomer 66: (6.3 mg, 0.012 mmol, 19.63 % yield).LCMS (M+H)= 508.0; Retention time (10 mM NH4HCO3) = 1.595 min. lH NMR (400 MHz, MeOD) δ 8.23(d,J=2.7Hz,1H),7.98(s,1H),7.42(dd,J=8.6,2.8Hz,1H),7.33(d,J=8.6Hz, 1H),5.78(s,1H),3.94-3.84(m,2H),2.52(s,3H),2.18-1.12(m,17H),1.07(s,9H), 0.62-0.52(m,2H),0.31(q,J=4.6Hz,2H).",
          "refs": null
      }},
      {{
          "compound_id": "Example 65 and 66.Step 3",
          "iupac_name": "(2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetic acid",
          "structure_id": "page_76.mol_1",
          "detail_ids": [
              "p76.i7",
              "p77.i0"
          ],
          "detail": "Step 3: The diastereomers of (2S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetic acid (32.1 mg,\n0.063 mmol) were separated by SFC [Column AD-H 4.6x 100 mm; 5 um; Co-Solvent EtOH (1%ammonia/methanol)] to obtain\nFirst eluting diastereomer 65:(9.6 mg, 0.019 mmol,29.9% yield).LCMS(M+H)= 508.2;Retention time (10 mM NH4HCO3) =1.605 min. lHNMR (400 MHz, MeOD) δ 8.35(d,J=2.8Hz,1H),8.11 (s,1H), 7.54(dd,J=8.6,2.9 Hz, 1H), 7.45(d, J=8.6 Hz, 1H),5.80(s,1H),4.00(d,J=7.0Hz,2H),2.66(s,3H),2.31-1.25(m,17H),1.18(s,9H), 0.74-0.65(m,2H),0.50-0.34(m,2H)and Second eluting diastereomer 66: (6.3 mg, 0.012 mmol, 19.63 % yield).LCMS (M+H)= 508.0; Retention time (10 mM NH4HCO3) = 1.595 min. lH NMR (400 MHz, MeOD) δ 8.23(d,J=2.7Hz,1H),7.98(s,1H),7.42(dd,J=8.6,2.8Hz,1H),7.33(d,J=8.6Hz, 1H),5.78(s,1H),3.94-3.84(m,2H),2.52(s,3H),2.18-1.12(m,17H),1.07(s,9H), 0.62-0.52(m,2H),0.31(q,J=4.6Hz,2H).",
          "refs": null
      }}
  ]
}}
```
"""

isomer_few_shots2 = \
"""
## fewshot3
The current structure follows the following format:  
1. First, this is an isomer example, with the Example Name shown at the top.
2. Two structure_id values appear sequentially within the <mol> tags.
3. The final step is associated with two structures. Both must be mapped back to the same Example Name, but output as separate records.
Input:
```
<text id=p81.i1>
Example 71 and 72
</text>
<mol id=p81.i2>
page_81.mol_0
</mol>
<text id=p81.i3>
First eluting isomer
(2S)-2-(tert-Butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-
pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetic acid
Step 1: To a solution of isopropyl (2S)-2-(tert-butoxy)-2-(5-hydroxy-6'-methyl-4'-
(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetate (50mg, 0.101 mmol)in (10
mL) was added K2CO3 (41.8 mg, 0.303 mmol) and 2-(tetrahydro-2H-pyran-4-yl)ethyl
methanesulfonate (31.5 mg,0.151 mmol).The mixture was stirred for 20 hours at 45°℃,
diluted with water and ethyl acetate(30 mL), organic layer separated, washed with brine
(20 mL), dried over Na2SO4 and concentrated to obtain a crude product which was purified
by silica gel chromatography eluting with ether acetate/ petroleum ether (from 10:1 to 1:1)
to afford isopropyl (2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-
(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetate (52 mg,0.082 mmol,
81% yield) as yellow oil. LCMS (M+H)=608.2; Retention time (10 mM NH4HCO3)=
2.649 min.
</text>
<text id=p81.i8>
Step 2: To a solution of isopropyl (2S)-2-(tert-butoxy)-2-(6'-methyl-4'-
(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-
5'-yl)acetate (52 mg, 0.086 mmol) in methanol (10 mL) and water (2 mL) was added
sodium hydroxide (10.27 mg,0.257 mmol) and stirred for 20 hours at 100°C.The mixture
was concentrated under vacuo, diluted with HCl (1N,0.5 ml) and ethyl acetate (5ml).
Organic layer separated and concentrated to give crude product which was purified by
</text>
<mol id=p81.i11>
page_81.mol_1
</mol>
<text id=p81.i12>
Second eluting isomer
</text>
<text id=p82.i0>
Prep-HPLC {{Instrument Gilson 281 (PHG-009); Column Xtimate Prep C18 OBD, 21.2x
250 mm,10 um;Mobile Phase A: Water(10 mM NH4HCO3);B: MeCN;Gradient 40-
68%B in 8.0 min, stop at 13.0 min; Flow Rate (ml/min) 30.00}} to give (2S)-2-(tert-
butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-
yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetic acid (21.5 mg,0.038 mmol, 44.4% yield) as white
solid.LCMS (M+H)=566.2;Retention time(10 mM NH4HCO3)=1.560 min.
</text>
<text id=p82.i2>
Step 3: The diastereomers of (2S)-2-(tert-butoxy)-2-(6'-methyl-4'-
(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-
5'-yl)acetic acid (21.5 mg, 0.038 mmol) were separated by SFC [Column IC (4.6 x 100
mm; 5 um); Co-Solvent MeOH (0.2%ammonia/methano)] to obtain
First eluting diastereomer 71:(4.5 mg, 7.70 umol, 20.27% yield).LCMS (M+H)=566.1;
Retention time(10 mM NH4HCO3)=1.558 min.lHNMR(400 MHz,MeOD) 8 8.37(d,J
=2.8Hz,1H),8.13(s,1H),7.57(dd,J=8.6,2.9Hz,1H),7.46(d,J=8.6Hz,1H),5.82(s,
1H), 4.23 (t, J=6.2 Hz,2H),3.97(dd, J= 11.1,3.4Hz,2H),3.47(td,J=11.9, 1.9 Hz,
2H),2.66(s,3H),1.93-1.29(m,23H),1.20(s,9H) and
Second eluting diastereomer 72: (3.7mg, 6.54 umol, 17.21 % yield). LCMS (M+H)=
566.2 ;Retention time (10 mM NH4HCO3)= 1.545 min. lHNMR (400 MHz, MeOD)δ
8.26(d,J=2.7 Hz,1H),8.03 (s,1H),7.45(dd,J=8.6,2.9 Hz,1H),7.36(d,J=8.6Hz,
1H),5.83(s,1H),4.11(t,J=6.1Hz,2H),3.85 (dd,J=10.9,3.7Hz,2H),3.34(td, J=
11.9,2.0Hz,2H),2.52(s,3H),2.13-2.07(m,1H),1.98-1.16(m,23H),1.08(s,9H).
</text>
```
Output:
```json
{{
  "results": [
      {{
          "compound_id": "Example 71 and 72.Step 1",
          "iupac_name": "isopropyl (2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetate",
          "structure_id": "",
          "detail_ids": [
              "p81.i3"
          ],
          "detail": "Step 1: To a solution of isopropyl (2S)-2-(tert-butoxy)-2-(5-hydroxy-6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-[2,3'-bipyridin]-5'-yl)acetate (50mg, 0.101 mmol)in (10 mL) was added K2CO3 (41.8 mg, 0.303 mmol) and 2-(tetrahydro-2H-pyran-4-yl)ethyl methanesulfonate (31.5 mg,0.151 mmol).The mixture was stirred for 20 hours at 45°℃, diluted with water and ethyl acetate(30 mL), organic layer separated, washed with brine (20 mL), dried over Na2SO4 and concentrated to obtain a crude product which was purified by silica gel chromatography eluting with ether acetate/ petroleum ether (from 10:1 to 1:1) to afford isopropyl (2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetate (52 mg,0.082 mmol, 81% yield) as yellow oil. LCMS (M+H)=608.2; Retention time (10 mM NH4HCO3)= 2.649 min.",
          "refs": null
      }},
      {{
          "compound_id": "Example 71 and 72.Step 2",
          "iupac_name": "(2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetic acid",
          "structure_id": "",
          "detail_ids": [
              "p81.i8",
              "p82.i0"
          ],
          "detail": "Step 2: To a solution of isopropyl (2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetate (52 mg, 0.086 mmol) in methanol (10 mL) and water (2 mL) was added sodium hydroxide (10.27 mg,0.257 mmol) and stirred for 20 hours at 100°C.The mixture was concentrated under vacuo, diluted with HCl (1N,0.5 ml) and ethyl acetate (5ml). Organic layer separated and concentrated to give crude product which was purified by Prep-HPLC {{Instrument Gilson 281 (PHG-009); Column Xtimate Prep C18 OBD, 21.2x 250 mm,10 um;Mobile Phase A: Water(10 mM NH4HCO3);B: MeCN;Gradient 40-68%B in 8.0 min, stop at 13.0 min; Flow Rate (ml/min) 30.00}} to give (2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetic acid (21.5 mg,0.038 mmol, 44.4% yield) as white solid.LCMS (M+H)=566.2;Retention time(10 mM NH4HCO3)=1.560 min.",
          "refs": null
      }},
      {{
          "compound_id": "Example 71 and 72.Step 3",
          "iupac_name": "(2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetic acid",
          "structure_id": "page_81.mol_0",
          "detail_ids": [
              "p82.i2"
          ],
          "detail": "Step 3: The diastereomers of (2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetic acid (21.5 mg, 0.038 mmol) were separated by SFC [Column IC (4.6 x 100 mm; 5 um); Co-Solvent MeOH (0.2%ammonia/methano)] to obtain First eluting diastereomer 71:(4.5 mg, 7.70 umol, 20.27% yield).LCMS (M+H)=566.1; Retention time(10 mM NH4HCO3)=1.558 min.lHNMR(400 MHz,MeOD) 8 8.37(d,J =2.8Hz,1H),8.13(s,1H),7.57(dd,J=8.6,2.9Hz,1H),7.46(d,J=8.6Hz,1H),5.82(s, 1H), 4.23 (t, J=6.2 Hz,2H),3.97(dd, J= 11.1,3.4Hz,2H),3.47(td,J=11.9, 1.9 Hz, 2H),2.66(s,3H),1.93-1.29(m,23H),1.20(s,9H) and Second eluting diastereomer 72: (3.7mg, 6.54 umol, 17.21 % yield). LCMS (M+H)= 566.2 ;Retention time (10 mM NH4HCO3)= 1.545 min. lHNMR (400 MHz, MeOD)δ 8.26(d,J=2.7 Hz,1H),8.03 (s,1H),7.45(dd,J=8.6,2.9 Hz,1H),7.36(d,J=8.6Hz, 1H),5.83(s,1H),4.11(t,J=6.1Hz,2H),3.85 (dd,J=10.9,3.7Hz,2H),3.34(td, J= 11.9,2.0Hz,2H),2.52(s,3H),2.13-2.07(m,1H),1.98-1.16(m,23H),1.08(s,9H).",
          "refs": null
      }},
      {{
          "compound_id": "Example 71 and 72.Step 3",
          "iupac_name": "(2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetic acid",
          "structure_id": "page_81.mol_1",
          "detail_ids": [
              "p82.i2"
          ],
          "detail": "Step 3: The diastereomers of (2S)-2-(tert-butoxy)-2-(6'-methyl-4'-(octahydroisoquinolin-2(1H)-yl)-5-(2-(tetrahydro-2H-pyran-4-yl)ethoxy)-[2,3'-bipyridin]-5'-yl)acetic acid (21.5 mg, 0.038 mmol) were separated by SFC [Column IC (4.6 x 100 mm; 5 um); Co-Solvent MeOH (0.2%ammonia/methano)] to obtain First eluting diastereomer 71:(4.5 mg, 7.70 umol, 20.27% yield).LCMS (M+H)=566.1; Retention time(10 mM NH4HCO3)=1.558 min.lHNMR(400 MHz,MeOD) 8 8.37(d,J =2.8Hz,1H),8.13(s,1H),7.57(dd,J=8.6,2.9Hz,1H),7.46(d,J=8.6Hz,1H),5.82(s, 1H), 4.23 (t, J=6.2 Hz,2H),3.97(dd, J= 11.1,3.4Hz,2H),3.47(td,J=11.9, 1.9 Hz, 2H),2.66(s,3H),1.93-1.29(m,23H),1.20(s,9H) and Second eluting diastereomer 72: (3.7mg, 6.54 umol, 17.21 % yield). LCMS (M+H)= 566.2 ;Retention time (10 mM NH4HCO3)= 1.545 min. lHNMR (400 MHz, MeOD)δ 8.26(d,J=2.7 Hz,1H),8.03 (s,1H),7.45(dd,J=8.6,2.9 Hz,1H),7.36(d,J=8.6Hz, 1H),5.83(s,1H),4.11(t,J=6.1Hz,2H),3.85 (dd,J=10.9,3.7Hz,2H),3.34(td, J= 11.9,2.0Hz,2H),2.52(s,3H),2.13-2.07(m,1H),1.98-1.16(m,23H),1.08(s,9H).",
          "refs": null
      }}
  ]
}}
```
"""

base_few_shot1 = \
"""
## fewshot
Input:
```
<text id=p45.i7>
Example 39
</text>
<mol id=p46.i0>
page_46.mol_0
</mol>
<text id=p46.i1>
(S)-2-tert-Butoxy-2-(5-(cyclopropylmethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-
methyl-2,3'-bipyridin-5'-yl)acetic acid
Step 1: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(4'-(4-ethyl-4-methylpiperidin-1-
yl)-5-hydroxy-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (30 mg, 0.062 mmol) in DMF (10
mL) was added K2CO3 (42.9 mg, 0.310 mmol) and (bromomethyl)cyclopropane (25.1 mg,
0.186 mmol). Then, the mixture was stirred for 20 hours at 45℃ and diluted with water
and ethyl acetate (30 mL). Organic layer separated, washed with brine (20 mL), dried over
Na2SO4 and concentrated to obtain a crude product, which was purified by silica gel
chromatography eluting with ethyl acetate/petroleum ether (from 10:1 to 1:1) to afford
isopropyl (S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-4'-(4-ethyl-4-methylpiperidin-1-
yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (30 mg, 0.018 mmol, 29.7% yield) as a yellow
oil.LC;MS(M+H)=538.3; Retention time(10 mM NH4HCO3)=2.005.
</text>
<text id=p46.i4>
Step 2: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-
4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (30 mg,0.056
mmol) in methanol (10 mL) and water(2 mL) was added sodium hydroxide (6.69 mg,
0.167 mmol) and stirred for 20 hours at 100C.The mixture was concentrated under
vacuo, diluted with HCl (1N,0.5 ml), extracted with ethyl acetate (5 ml) and concentrated
to give crude product. The crude product was purified by Prep-HPLC {{Instrument Gilson
281(PHG-009); Column Xtimate Prep C18 OBD,21.2x250 mm,10 um; Mobile Phase
A: water (10 mM NH4HCO3);B:MeCN;Gradient 40-68%B in 8.0 min, stop at 13.0 min;
Flow Rate (ml/min) 30.00}} to give (S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-4'-(4-
ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetic acid (10.1 mg,0.020
mmol, 36.5 % yield) as white solid.LCMS (M+H)=496.2; Retention time (10 mM
NH4HCO3)= 1.573. lH NMR (400 MHz, MeOD) δ8.37(d, J=2.7Hz, 1H), 8.16(s, 1H),
7.55 (dd, J= 8.6, 2.9 Hz,1H), 7.46 (d, J=8.5 Hz,1H),5.82(s,1H),4.00 (d, J=7.0 Hz,
2H),3.09-2.53(m,7H),1.58-1.27(m,7H),1.21(s,9H),0.91-0.76(m,6H),0.73-0.63
(m,2H),0.53-0.30(m,2H).
</text>
```
Output:
```json
{{
    "results": [
      {{
          "compound_id": "Example 39.Step 1",
          "iupac_name": "isopropyl (S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate",
          "structure_id": "",
          "detail_ids": [
              "p46.i1"
          ],
          "detail": "Step 1: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(4'-(4-ethyl-4-methylpiperidin-1-yl)-5-hydroxy-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (30 mg, 0.062 mmol) in DMF (10 mL) was added K2CO3 (42.9 mg, 0.310 mmol) and (bromomethyl)cyclopropane (25.1 mg, 0.186 mmol). Then, the mixture was stirred for 20 hours at 45℃ and diluted with water and ethyl acetate (30 mL). Organic layer separated, washed with brine (20 mL), dried over Na2SO4 and concentrated to obtain a crude product, which was purified by silica gel chromatography eluting with ethyl acetate/petroleum ether (from 10:1 to 1:1) to afford isopropyl (S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (30 mg, 0.018 mmol, 29.7% yield) as a yellow oil.LC;MS(M+H)=538.3; Retention time(10 mM NH4HCO3)=2.005.",
          "refs": null
      }},
      {{
          "compound_id": "Example 39.Step 2",
          "iupac_name": "(S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetic acid",
          "structure_id": "page_46.mol_0",
          "detail_ids": [
              "p46.i4"
          ],
          "detail": "Step 2: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (30 mg,0.056 mmol) in methanol (10 mL) and water(2 mL) was added sodium hydroxide (6.69 mg, 0.167 mmol) and stirred for 20 hours at 100C.The mixture was concentrated under vacuo, diluted with HCl (1N,0.5 ml), extracted with ethyl acetate (5 ml) and concentrated to give crude product. The crude product was purified by Prep-HPLC {{Instrument Gilson 281(PHG-009); Column Xtimate Prep C18 OBD,21.2x250 mm,10 um; Mobile Phase A: water (10 mM NH4HCO3);B:MeCN;Gradient 40-68%B in 8.0 min, stop at 13.0 min; Flow Rate (ml/min) 30.00}} to give (S)-2-(tert-butoxy)-2-(5-(cyclopropylmethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetic acid (10.1 mg,0.020 mmol, 36.5 % yield) as white solid.LCMS (M+H)=496.2; Retention time (10 mM NH4HCO3)= 1.573. lH NMR (400 MHz, MeOD) δ8.37(d, J=2.7Hz, 1H), 8.16(s, 1H), 7.55 (dd, J= 8.6, 2.9 Hz,1H), 7.46 (d, J=8.5 Hz,1H),5.82(s,1H),4.00 (d, J=7.0 Hz, 2H),3.09-2.53(m,7H),1.58-1.27(m,7H),1.21(s,9H),0.91-0.76(m,6H),0.73-0.63 (m,2H),0.53-0.30(m,2H).",
          "refs": null
      }}
  ]
}}
```
"""

base_few_shot2 = \
"""
## fewshot
Input:
```
<text id=p43.i5>
Example 37
</text>
<mol id=p43.i6>
page_43.mol_0
</mol>
<text id=p43.i7>
(S)-2-tert-Butoxy-2-(5-butoxy-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-2,3'-
bipyridin-5'-yl)acetic acid
Step 1: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(4'-(4-ethyl-4-
methylpiperidin-1-yl)-5-hydroxy-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (50 mg,0.103
mmol) in DMF (10 mL) was added K2CO3(14.29 mg,0.103 mmol) and 1-bromobutane
(14.17 mg,0.103 mmol). Then, the mixture was stirred for 20 hours at 45 °℃ and diluted
with water and ethyl acetate (30 mL). Organic layer separated, washed with brine (20 mL),
dried over Na2SO4 and concentrated to obtain a crude product, which was purified by silica
</text>
<text id=p44.i0>
gel chromatography eluting with ethyl acetate/petroleum ether (from 10:1 to 1:1) to afford
isopropyl (S)-2-(tert-butoxy)-2-(5-butoxy-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-
[2,3'-bipyridin]-5'-yl)acetate (43 mg, 0.080 mmol, 77% yield) as a yellow oil.LCMS(M+
H)=540.2; Retention time (10 mM NH4HCO3)=2.758.
</text>
<text id=p44.i1>
Step 2: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(5-butoxy-4'-(4-ethyl-4-
methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (52 mg, 0.096 mmol) in
methanol (10 mL) and water (2 mL) was added sodium hydroxide (11.56 mg, 0.289 mmol)
and stirred for 20 hours at 100°C.The mixture was concentrated under vacuo, diluted with
HCl (1N,0.5 ml), extracted with ethyl acetate (5 ml) and concentrated to give crude
product. The crude product was purified by Prep-HPLC {{Instrument Gilson 281 (PHG-
009); Column Xtimate Prep C18 OBD,21.2 x 250 mm,10 um; Mobile Phase A:water (10
mM NH4HCO3); B:MeCN; Gradient 40-68%B in 8.0 min,stop at 13.0 min; Flow Rate
(ml/min)30.00}} togive (S)-2-(tert-butoxy)-2-(5-butoxy-4'-(4-ethyl-4-methylpiperidin-1-
yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetic acid (21.6 mg,0.042 mmol, 43.9 % yield) as
white solid.LCMS(M+H)=498.1; Retention time(10 mM NH4HCO3)=1.716.lH
NMR(400 MHz,MeOD)δ8.36(d,J=2.8Hz,1H), 8.17(s,1H), 7.56(dd, J=8.6,2.9 Hz,
1H),7.47(d,J=8.6Hz,1H),5.82(s,1H),4.16(t,J=6.4Hz,2H),2.30-2.66(m,7H),
1.91-1.77(m,2H),1.64-1.25(m,8H),1.21(s,9H),1.04(t,J=7.4Hz,3H),0.88-0.77
(m, 6H).
</text>
<text id=p44.i4>
Example 38
</text>
<mol id=p44.i5>
page_44.mol_0
</mol>
<text id=p44.i6>
(S)-2-tert-Butoxy-2-(5-(2-(1,3-dimethyl-1H-pyrazol-4-yl)ethoxy)-4'-(4-ethyl-4-
methylpiperidin-1-yl)-6'-methyl-2,3'-bipyridin-5'-yl)acetic acid
Step 1: To a solution of 2-(1,3-dimethyl-1H-pyrazol-4-yl)ethan-1-ol (250 mg,1.783
mmol) and triethylamine (271 mg,2.68 mmol) in DCM (10 mL) was added methanesulfonyl
chloride (225 mg, 1.962 mmol) at 0°℃. The mixture was stirred at rt for 1 h. The mixture
was taken up into aqueous Na2CO3 (20 mL) and extracted with DCM (10 ml X 3). The
</text>
<text id=p45.i0>
combined organic layers were washed with brine, dried over Na2SO4, concentrated to afford
2-(1,3-dimethyl-1H-pyrazol-4-yl)ethyl methanesulfonate (300 mg, 1.100 mmol, 61.7 %
yield) as oil which was used in the next step without further purification. LCMS: retention
time = 1.22 min, m/z = 219 [M+H]<sup>+</sup>, purity: 80% (214 nm).
</text>
<text id=p45.i1>
Step 2: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(4'-(4-ethyl-4-
methylpiperidin-1-yl)-5-hydroxy-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (50 mg, 0.103
mmol) in DMF (10 mL) was added K<sub>2</sub>CO<sub>3</sub> (71.4 mg, 0.517 mmol) and 2-(1,3-dimethyl-
1H-pyrazol-4-yl)ethyl methanesulfonate (67.7 mg, 0.310 mmol). Then, the mixture was
stirred for 20 hours at 45 °C and diluted with water and ethyl acetate (30 mL). Organic
layer separated, washed with brine (20 mL), dried over Na2SO<sub>4</sub> and concentrated to obtain
a crude product, which was purified by silica gel chromatography eluting with ethyl
acetate/petroleum ether (from 10:1 to 1:1) to afford isopropyl (S)-2-(tert-butoxy)-2-(5-(2-
(1,3-dimethyl-1H-pyrazol-4-yl)ethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-
bipyridin]-5'-yl)acetate (41 mg, 0.068 mmol, 65.5 % yield) as a yellow oil. LCMS (M + H)
= 606.2; Retention time (10 mM NH<sub>4</sub>HCO<sub>3</sub>) = 2.234.
</text>
<text id=p45.i3>
Step 3: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(5-(2-(1,3-dimethyl-1H-
pyrazol-4-yl)ethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-
yl)acetate (41 mg, 0.068 mmol) in methanol (10 mL) and water (2 mL) was added sodium
hydroxide (8.12 mg, 0.203 mmol) and stirred for 20 hours at 100 °C. The mixture was
concentrated under vacuo, diluted with HCl (1N, 0.5 ml), extracted with ethyl acetate (5
ml) and concentrated to give crude product. The crude product was purified by Prep-HPLC
{{Instrument Gilson 281 (PHG-009); Column Xtimate Prep C18 OBD, 21.2 x 250 mm, 10
um; Mobile Phase A: water (10 mM NH4HCO3); B: MeCN; Gradient 40-68%B in 8.0
min, stop at 13.0 min; Flow Rate (ml/min) 30.00}} to give (S)-2-(tert-butoxy)-2-(5-(2-(1,3-
dimethyl-1H-pyrazol-4-yl)ethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-
bipyridin]-5'-yl) acetic acid (17.3 mg, 0.031 mmol, 45.3 % yield) as white solid. LCMS (M
+ H) = 564.2; Retention time (10 mM NH<sub>4</sub>HCO<sub>3</sub>) = 1.452. <sup>1</sup>H NMR (400 MHz, MeOD) δ
8.38 (d, J = 2.7 Hz, 1H), 8.16 (s, 1H), 7.56 (dd, J = 8.6, 2.9 Hz, 1H), 7.47 (d, J = 7.8 Hz,
2H), 5.82 (s, 1H), 4.25 (t, J = 6.7 Hz, 2H), 3.80 (s, 3H), 3.23-2.57 (m, 9H), 2.25 (s, 3H),
1.61-1.23 (m, 6H), 1.21 (s, 9H), 0.87- 0.74 (m, 6H).
</text>
```
Output:
```json
{{
    "results": [
        {{
        "compound_id": "Example 37.Step 1",
        "iupac_name": "isopropyl (S)-2-(tert-butoxy)-2-(5-butoxy-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate",
        "structure_id": "",
        "detail_ids": [
            "p43.i7",
            "p44.i0"
        ],
        "detail": "Step 1: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(4'-(4-ethyl-4-methylpiperidin-1-yl)-5-hydroxy-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (50 mg,0.103 mmol) in DMF (10 mL) was added K2CO3(14.29 mg,0.103 mmol) and 1-bromobutane (14.17 mg,0.103 mmol). Then, the mixture was stirred for 20 hours at 45 °℃ and diluted with water and ethyl acetate (30 mL). Organic layer separated, washed with brine (20 mL), dried over Na2SO4 and concentrated to obtain a crude product, which was purified by silica\ngel chromatography eluting with ethyl acetate/petroleum ether (from 10:1 to 1:1) to afford isopropyl (S)-2-(tert-butoxy)-2-(5-butoxy-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (43 mg, 0.080 mmol, 77% yield) as a yellow oil.LCMS(M+ H)=540.2; Retention time (10 mM NH4HCO3)=2.758.",
        "refs": null
        }},
        {{
        "compound_id": "Example 37.Step2",
        "iupac_name": "(S)-2-(tert-butoxy)-2-(5-butoxy-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetic acid",
        "structure_id": "page_43.mol_0",
        "detail_ids": [
            "p44.i1"
        ],
        "detail": "Step 2: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(5-butoxy-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (52 mg, 0.096 mmol) in methanol (10 mL) and water (2 mL) was added sodium hydroxide (11.56 mg, 0.289 mmol) and stirred for 20 hours at 100°C.The mixture was concentrated under vacuo, diluted with HCl (1N,0.5 ml), extracted with ethyl acetate (5 ml) and concentrated to give crude product. The crude product was purified by Prep-HPLC {{Instrument Gilson 281 (PHG-009); Column Xtimate Prep C18 OBD,21.2 x 250 mm,10 um; Mobile Phase A:water (10 mM NH4HCO3); B:MeCN; Gradient 40-68%B in 8.0 min,stop at 13.0 min; Flow Rate (ml/min)30.00}} togive (S)-2-(tert-butoxy)-2-(5-butoxy-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetic acid (21.6 mg,0.042 mmol, 43.9 % yield) as white solid.LCMS(M+H)=498.1; Retention time(10 mM NH4HCO3)=1.716.lH NMR(400 MHz,MeOD)δ8.36(d,J=2.8Hz,1H), 8.17(s,1H), 7.56(dd, J=8.6,2.9 Hz, 1H),7.47(d,J=8.6Hz,1H),5.82(s,1H),4.16(t,J=6.4Hz,2H),2.30-2.66(m,7H), 1.91-1.77(m,2H),1.64-1.25(m,8H),1.21(s,9H),1.04(t,J=7.4Hz,3H),0.88-0.77 (m, 6H).",
        "refs": null
        }},
        {{
        "compound_id": "Example 38.Step 1",
        "iupac_name": "2-(1,3-dimethyl-1H-pyrazol-4-yl)ethyl methanesulfonate",
        "structure_id": "",
        "detail_ids": [
            "p44.i6",
            "p45.i0"
        ],
        "detail": "Step 1: To a solution of 2-(1,3-dimethyl-1H-pyrazol-4-yl)ethan-1-ol (250 mg,1.783 mmol) and triethylamine (271 mg,2.68 mmol) in DCM (10 mL) was added methanesulfonyl chloride (225 mg, 1.962 mmol) at 0°℃. The mixture was stirred at rt for 1 h. The mixture was taken up into aqueous Na2CO3 (20 mL) and extracted with DCM (10 ml X 3). The\ncombined organic layers were washed with brine, dried over Na2SO4, concentrated to afford 2-(1,3-dimethyl-1H-pyrazol-4-yl)ethyl methanesulfonate (300 mg, 1.100 mmol, 61.7 % yield) as oil which was used in the next step without further purification. LCMS: retention time = 1.22 min, m/z = 219 [M+H]<sup>+</sup>, purity: 80% (214 nm).",
        "refs": null
        }},
        {{
        "compound_id": "Example 38.Step 2",
        "iupac_name": "isopropyl (S)-2-(tert-butoxy)-2-(5-(2-(1,3-dimethyl-1H-pyrazol-4-yl)ethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate",
        "structure_id": "",
        "detail_ids": [
            "p45.i1"
        ],
        "detail": "Step 2: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(4'-(4-ethyl-4-methylpiperidin-1-yl)-5-hydroxy-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (50 mg, 0.103 mmol) in DMF (10 mL) was added K<sub>2</sub>CO<sub>3</sub> (71.4 mg, 0.517 mmol) and 2-(1,3-dimethyl-1H-pyrazol-4-yl)ethyl methanesulfonate (67.7 mg, 0.310 mmol). Then, the mixture was stirred for 20 hours at 45 °C and diluted with water and ethyl acetate (30 mL). Organic layer separated, washed with brine (20 mL), dried over Na2SO<sub>4</sub> and concentrated to obtain a crude product, which was purified by silica gel chromatography eluting with ethyl acetate/petroleum ether (from 10:1 to 1:1) to afford isopropyl (S)-2-(tert-butoxy)-2-(5-(2-(1,3-dimethyl-1H-pyrazol-4-yl)ethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (41 mg, 0.068 mmol, 65.5 % yield) as a yellow oil. LCMS (M + H) = 606.2; Retention time (10 mM NH<sub>4</sub>HCO<sub>3</sub>) = 2.234.",
        "refs": null
        }},
        {{
        "compound_id": "Example 38.Step 3",
        "iupac_name": "(S)-2-(tert-butoxy)-2-(5-(2-(1,3-dimethyl-1H-pyrazol-4-yl)ethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl) acetic acid",
        "structure_id": "page_44.mol_0",
        "detail_ids": [
            "p45.i3"
        ],
        "detail": "Step 3: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(5-(2-(1,3-dimethyl-1H-pyrazol-4-yl)ethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (41 mg, 0.068 mmol) in methanol (10 mL) and water (2 mL) was added sodium hydroxide (8.12 mg, 0.203 mmol) and stirred for 20 hours at 100 °C. The mixture was concentrated under vacuo, diluted with HCl (1N, 0.5 ml), extracted with ethyl acetate (5 ml) and concentrated to give crude product. The crude product was purified by Prep-HPLC {{Instrument Gilson 281 (PHG-009); Column Xtimate Prep C18 OBD, 21.2 x 250 mm, 10 um; Mobile Phase A: water (10 mM NH4HCO3); B: MeCN; Gradient 40-68%B in 8.0 min, stop at 13.0 min; Flow Rate (ml/min) 30.00}} to give (S)-2-(tert-butoxy)-2-(5-(2-(1,3-dimethyl-1H-pyrazol-4-yl)ethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl) acetic acid (17.3 mg, 0.031 mmol, 45.3 % yield) as white solid. LCMS (M + H) = 564.2; Retention time (10 mM NH<sub>4</sub>HCO<sub>3</sub>) = 1.452. <sup>1</sup>H NMR (400 MHz, MeOD) δ 8.38 (d, J = 2.7 Hz, 1H), 8.16 (s, 1H), 7.56 (dd, J = 8.6, 2.9 Hz, 1H), 7.47 (d, J = 7.8 Hz, 2H), 5.82 (s, 1H), 4.25 (t, J = 6.7 Hz, 2H), 3.80 (s, 3H), 3.23-2.57 (m, 9H), 2.25 (s, 3H), 1.61-1.23 (m, 6H), 1.21 (s, 9H), 0.87- 0.74 (m, 6H).",
        "refs": null
        }}
    ]
}}
```
"""

scheme_few_shot = \
"""
## fewshot
1. refs is only used to record other compound identifiers explicitly referenced during the synthesis of this product (e.g., Example XX). If no such identifiers are mentioned, set refs: null.
Input:
```
<scheme id=p12.i9>
| id             | reactant      | condition   | product       |
|:---------------|:--------------|:------------|:--------------|
| page12.scheme0 | page_12.mol_0 |             | page_12.mol_1 |
</scheme>
<text id=p12.i10>
To a stirred solution of 2-methylpyridin-4-ol (8.0 g, 73 mmol)in dichloromethane
(90 ml) and MeOH(11 ml) was added tert-butylamine (15.7 ml,148 mmol) and the
mixture was cooled to 0 °C. Bromine (7.55 ml,147 mmol) was added dropwise over a 20
minute period. The reaction mixture was stirred at rt for 2 hours. Then the resulting slurry
was filtered through a buchner funnel and the solid was washed with methanol (100 ml)
and dried overnight to afford 3,5-dibromo-2-methylpyridin-4-ol (10g,37.5 mmol, 51.1%
yield). LCMS Method 4:retention time = 0.704 min.; observed ion =267.8.lH NMR (500
MHz,DMSO-d6)δ12.33(brs,1H),8.21(s,1H),2.40(s,3H).
</text>
```
Output:
```json
{{
    "results": [
        {{
        "compound_id": "",
        "iupac_name": "3,5-dibromo-2-methylpyridin-4-ol",
        "structure_id": "page_12.mol_1",
        "detail_ids": [
            "p12.i10"
        ],
        "detail": "To a stirred solution of 2-methylpyridin-4-ol (8.0 g, 73 mmol)in dichloromethane (90 ml) and MeOH(11 ml) was added tert-butylamine (15.7 ml,148 mmol) and the mixture was cooled to 0 °C. Bromine (7.55 ml,147 mmol) was added dropwise over a 20 minute period. The reaction mixture was stirred at rt for 2 hours. Then the resulting slurry was filtered through a buchner funnel and the solid was washed with methanol (100 ml) and dried overnight to afford 3,5-dibromo-2-methylpyridin-4-ol (10g,37.5 mmol, 51.1% yield). LCMS Method 4:retention time = 0.704 min.; observed ion =267.8.lH NMR (500 MHz,DMSO-d6)δ12.33(brs,1H),8.21(s,1H),2.40(s,3H).",
        "refs": null
        }}
    ]
}}
```
"""

PATENT_SYNTHESIS_SYSTEM_PROMPT_fewshot_123 = """
You are a chemical synthesis extraction agent. Extract **each synthesis step** from chemical patent text, with no inference across steps. Preserve wording and IDs exactly.

# Input
Patent text is tagged as:
- <text id=...> ... </text>
- <mol id=...> ... </mol>
- <table id=...> ... </table>
- <scheme id=...> ... </scheme>
Tags are top-level, ordered, and IDs must not be changed.

# Extraction Fields
1. compound_id  
   - Use explicit product labels (e.g., "Compound 2", "Intermediate A").  
   - If only section title defines the final product, assign section title (only last step).  
   - Otherwise "".
2. iupac_name  
   - Use if explicitly given; otherwise "". No inference.
3. structure_id  
   - Only link <mol> ID if it shows the **final product** of the whole Example/Section. Else "".
4. detail_ids  
   - List of <text id=...> blocks describing procedure (exclude pure analytical data).
5. detail  
   - Concatenated verbatim text of detail_ids. No paraphrasing.
6. refs  
   - Compound identifiers referenced as inputs. Use exact labels. If none, null.

# Output Format
```json
{{
  "results": [
    {{
      "compound_id": "...",
      "iupac_name": "...",
      "structure_id": "...",
      "detail_ids": ["..."],
      "detail": "...",
      "refs": [...] or null
    }}
  ]
}}
```

# Rules
1. One record per step; split at "Step" or clear process transitions.
2. Never merge steps.
3. No cross-step inference.
4. Use section title as compound_id only for the last product-forming step.
5. Accept phrases like "title compound" only as reference, not as identifiers.

# Restriction
1. Retain all <sub> and <sup> tags and their contents exactly as in the source text.

# Few-Shots
Here are some few-shots:
## fewshot1
Input:
```
<text id=p43.i5>
Example 37
</text>
<mol id=p43.i6>
page_43.mol_0
</mol>
<text id=p43.i7>
(S)-2-tert-Butoxy-2-(5-butoxy-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-2,3'-
bipyridin-5'-yl)acetic acid
Step 1: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(4'-(4-ethyl-4-
methylpiperidin-1-yl)-5-hydroxy-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (50 mg,0.103
mmol) in DMF (10 mL) was added K2CO3(14.29 mg,0.103 mmol) and 1-bromobutane
(14.17 mg,0.103 mmol). Then, the mixture was stirred for 20 hours at 45 °℃ and diluted
with water and ethyl acetate (30 mL). Organic layer separated, washed with brine (20 mL),
dried over Na2SO4 and concentrated to obtain a crude product, which was purified by silica
</text>
<text id=p44.i0>
gel chromatography eluting with ethyl acetate/petroleum ether (from 10:1 to 1:1) to afford
isopropyl (S)-2-(tert-butoxy)-2-(5-butoxy-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-
[2,3'-bipyridin]-5'-yl)acetate (43 mg, 0.080 mmol, 77% yield) as a yellow oil.LCMS(M+
H)=540.2; Retention time (10 mM NH4HCO3)=2.758.
</text>
<text id=p44.i1>
Step 2: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(5-butoxy-4'-(4-ethyl-4-
methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (52 mg, 0.096 mmol) in
methanol (10 mL) and water (2 mL) was added sodium hydroxide (11.56 mg, 0.289 mmol)
and stirred for 20 hours at 100°C.The mixture was concentrated under vacuo, diluted with
HCl (1N,0.5 ml), extracted with ethyl acetate (5 ml) and concentrated to give crude
product. The crude product was purified by Prep-HPLC {{Instrument Gilson 281 (PHG-
009); Column Xtimate Prep C18 OBD,21.2 x 250 mm,10 um; Mobile Phase A:water (10
mM NH4HCO3); B:MeCN; Gradient 40-68%B in 8.0 min,stop at 13.0 min; Flow Rate
(ml/min)30.00}} togive (S)-2-(tert-butoxy)-2-(5-butoxy-4'-(4-ethyl-4-methylpiperidin-1-
yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetic acid (21.6 mg,0.042 mmol, 43.9 % yield) as
white solid.LCMS(M+H)=498.1; Retention time(10 mM NH4HCO3)=1.716.lH
NMR(400 MHz,MeOD)δ8.36(d,J=2.8Hz,1H), 8.17(s,1H), 7.56(dd, J=8.6,2.9 Hz,
1H),7.47(d,J=8.6Hz,1H),5.82(s,1H),4.16(t,J=6.4Hz,2H),2.30-2.66(m,7H),
1.91-1.77(m,2H),1.64-1.25(m,8H),1.21(s,9H),1.04(t,J=7.4Hz,3H),0.88-0.77
(m, 6H).
</text>
<text id=p44.i4>
Example 38
</text>
<mol id=p44.i5>
page_44.mol_0
</mol>
<text id=p44.i6>
(S)-2-tert-Butoxy-2-(5-(2-(1,3-dimethyl-1H-pyrazol-4-yl)ethoxy)-4'-(4-ethyl-4-
methylpiperidin-1-yl)-6'-methyl-2,3'-bipyridin-5'-yl)acetic acid
Step 1: To a solution of 2-(1,3-dimethyl-1H-pyrazol-4-yl)ethan-1-ol (250 mg,1.783
mmol) and triethylamine (271 mg,2.68 mmol) in DCM (10 mL) was added methanesulfonyl
chloride (225 mg, 1.962 mmol) at 0°℃. The mixture was stirred at rt for 1 h. The mixture
was taken up into aqueous Na2CO3 (20 mL) and extracted with DCM (10 ml X 3). The
</text>
<text id=p45.i0>
combined organic layers were washed with brine, dried over Na2SO4, concentrated to afford
2-(1,3-dimethyl-1H-pyrazol-4-yl)ethyl methanesulfonate (300 mg, 1.100 mmol, 61.7 %
yield) as oil which was used in the next step without further purification. LCMS: retention
time = 1.22 min, m/z = 219 [M+H]<sup>+</sup>, purity: 80% (214 nm).
</text>
<text id=p45.i1>
Step 2: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(4'-(4-ethyl-4-
methylpiperidin-1-yl)-5-hydroxy-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (50 mg, 0.103
mmol) in DMF (10 mL) was added K<sub>2</sub>CO<sub>3</sub> (71.4 mg, 0.517 mmol) and 2-(1,3-dimethyl-
1H-pyrazol-4-yl)ethyl methanesulfonate (67.7 mg, 0.310 mmol). Then, the mixture was
stirred for 20 hours at 45 °C and diluted with water and ethyl acetate (30 mL). Organic
layer separated, washed with brine (20 mL), dried over Na2SO<sub>4</sub> and concentrated to obtain
a crude product, which was purified by silica gel chromatography eluting with ethyl
acetate/petroleum ether (from 10:1 to 1:1) to afford isopropyl (S)-2-(tert-butoxy)-2-(5-(2-
(1,3-dimethyl-1H-pyrazol-4-yl)ethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-
bipyridin]-5'-yl)acetate (41 mg, 0.068 mmol, 65.5 % yield) as a yellow oil. LCMS (M + H)
= 606.2; Retention time (10 mM NH<sub>4</sub>HCO<sub>3</sub>) = 2.234.
</text>
<text id=p45.i3>
Step 3: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(5-(2-(1,3-dimethyl-1H-
pyrazol-4-yl)ethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-
yl)acetate (41 mg, 0.068 mmol) in methanol (10 mL) and water (2 mL) was added sodium
hydroxide (8.12 mg, 0.203 mmol) and stirred for 20 hours at 100 °C. The mixture was
concentrated under vacuo, diluted with HCl (1N, 0.5 ml), extracted with ethyl acetate (5
ml) and concentrated to give crude product. The crude product was purified by Prep-HPLC
{{Instrument Gilson 281 (PHG-009); Column Xtimate Prep C18 OBD, 21.2 x 250 mm, 10
um; Mobile Phase A: water (10 mM NH4HCO3); B: MeCN; Gradient 40-68%B in 8.0
min, stop at 13.0 min; Flow Rate (ml/min) 30.00}} to give (S)-2-(tert-butoxy)-2-(5-(2-(1,3-
dimethyl-1H-pyrazol-4-yl)ethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-
bipyridin]-5'-yl) acetic acid (17.3 mg, 0.031 mmol, 45.3 % yield) as white solid. LCMS (M
+ H) = 564.2; Retention time (10 mM NH<sub>4</sub>HCO<sub>3</sub>) = 1.452. <sup>1</sup>H NMR (400 MHz, MeOD) δ
8.38 (d, J = 2.7 Hz, 1H), 8.16 (s, 1H), 7.56 (dd, J = 8.6, 2.9 Hz, 1H), 7.47 (d, J = 7.8 Hz,
2H), 5.82 (s, 1H), 4.25 (t, J = 6.7 Hz, 2H), 3.80 (s, 3H), 3.23-2.57 (m, 9H), 2.25 (s, 3H),
1.61-1.23 (m, 6H), 1.21 (s, 9H), 0.87- 0.74 (m, 6H).
</text>
```
Output:
```json
{{
    "results": [
        {{
        "compound_id": "Example 37.Step 1",
        "iupac_name": "isopropyl (S)-2-(tert-butoxy)-2-(5-butoxy-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate",
        "structure_id": "",
        "detail_ids": [
            "p43.i7",
            "p44.i0"
        ],
        "detail": "Step 1: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(4'-(4-ethyl-4-methylpiperidin-1-yl)-5-hydroxy-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (50 mg,0.103 mmol) in DMF (10 mL) was added K2CO3(14.29 mg,0.103 mmol) and 1-bromobutane (14.17 mg,0.103 mmol). Then, the mixture was stirred for 20 hours at 45 °℃ and diluted with water and ethyl acetate (30 mL). Organic layer separated, washed with brine (20 mL), dried over Na2SO4 and concentrated to obtain a crude product, which was purified by silica\ngel chromatography eluting with ethyl acetate/petroleum ether (from 10:1 to 1:1) to afford isopropyl (S)-2-(tert-butoxy)-2-(5-butoxy-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (43 mg, 0.080 mmol, 77% yield) as a yellow oil.LCMS(M+ H)=540.2; Retention time (10 mM NH4HCO3)=2.758.",
        "refs": null
        }},
        {{
        "compound_id": "Example 37.Step 2",
        "iupac_name": "(S)-2-(tert-butoxy)-2-(5-butoxy-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetic acid",
        "structure_id": "page_43.mol_0",
        "detail_ids": [
            "p44.i1"
        ],
        "detail": "Step 2: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(5-butoxy-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (52 mg, 0.096 mmol) in methanol (10 mL) and water (2 mL) was added sodium hydroxide (11.56 mg, 0.289 mmol) and stirred for 20 hours at 100°C.The mixture was concentrated under vacuo, diluted with HCl (1N,0.5 ml), extracted with ethyl acetate (5 ml) and concentrated to give crude product. The crude product was purified by Prep-HPLC {{Instrument Gilson 281 (PHG-009); Column Xtimate Prep C18 OBD,21.2 x 250 mm,10 um; Mobile Phase A:water (10 mM NH4HCO3); B:MeCN; Gradient 40-68%B in 8.0 min,stop at 13.0 min; Flow Rate (ml/min)30.00}} togive (S)-2-(tert-butoxy)-2-(5-butoxy-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetic acid (21.6 mg,0.042 mmol, 43.9 % yield) as white solid.LCMS(M+H)=498.1; Retention time(10 mM NH4HCO3)=1.716.lH NMR(400 MHz,MeOD)δ8.36(d,J=2.8Hz,1H), 8.17(s,1H), 7.56(dd, J=8.6,2.9 Hz, 1H),7.47(d,J=8.6Hz,1H),5.82(s,1H),4.16(t,J=6.4Hz,2H),2.30-2.66(m,7H), 1.91-1.77(m,2H),1.64-1.25(m,8H),1.21(s,9H),1.04(t,J=7.4Hz,3H),0.88-0.77 (m, 6H).",
        "refs": null
        }},
        {{
        "compound_id": "Example 38.Step 1",
        "iupac_name": "2-(1,3-dimethyl-1H-pyrazol-4-yl)ethyl methanesulfonate",
        "structure_id": "",
        "detail_ids": [
            "p44.i6",
            "p45.i0"
        ],
        "detail": "Step 1: To a solution of 2-(1,3-dimethyl-1H-pyrazol-4-yl)ethan-1-ol (250 mg,1.783 mmol) and triethylamine (271 mg,2.68 mmol) in DCM (10 mL) was added methanesulfonyl chloride (225 mg, 1.962 mmol) at 0°℃. The mixture was stirred at rt for 1 h. The mixture was taken up into aqueous Na2CO3 (20 mL) and extracted with DCM (10 ml X 3). The\ncombined organic layers were washed with brine, dried over Na2SO4, concentrated to afford 2-(1,3-dimethyl-1H-pyrazol-4-yl)ethyl methanesulfonate (300 mg, 1.100 mmol, 61.7 % yield) as oil which was used in the next step without further purification. LCMS: retention time = 1.22 min, m/z = 219 [M+H]<sup>+</sup>, purity: 80% (214 nm).",
        "refs": null
        }},
        {{
        "compound_id": "Example 38.Step 2",
        "iupac_name": "isopropyl (S)-2-(tert-butoxy)-2-(5-(2-(1,3-dimethyl-1H-pyrazol-4-yl)ethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate",
        "structure_id": "",
        "detail_ids": [
            "p45.i1"
        ],
        "detail": "Step 2: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(4'-(4-ethyl-4-methylpiperidin-1-yl)-5-hydroxy-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (50 mg, 0.103 mmol) in DMF (10 mL) was added K<sub>2</sub>CO<sub>3</sub> (71.4 mg, 0.517 mmol) and 2-(1,3-dimethyl-1H-pyrazol-4-yl)ethyl methanesulfonate (67.7 mg, 0.310 mmol). Then, the mixture was stirred for 20 hours at 45 °C and diluted with water and ethyl acetate (30 mL). Organic layer separated, washed with brine (20 mL), dried over Na2SO<sub>4</sub> and concentrated to obtain a crude product, which was purified by silica gel chromatography eluting with ethyl acetate/petroleum ether (from 10:1 to 1:1) to afford isopropyl (S)-2-(tert-butoxy)-2-(5-(2-(1,3-dimethyl-1H-pyrazol-4-yl)ethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (41 mg, 0.068 mmol, 65.5 % yield) as a yellow oil. LCMS (M + H) = 606.2; Retention time (10 mM NH<sub>4</sub>HCO<sub>3</sub>) = 2.234.",
        "refs": null
        }},
        {{
        "compound_id": "Example 38.Step 3",
        "iupac_name": "(S)-2-(tert-butoxy)-2-(5-(2-(1,3-dimethyl-1H-pyrazol-4-yl)ethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl) acetic acid",
        "structure_id": "page_44.mol_0",
        "detail_ids": [
            "p45.i3"
        ],
        "detail": "Step 3: To a solution of isopropyl (S)-2-(tert-butoxy)-2-(5-(2-(1,3-dimethyl-1H-pyrazol-4-yl)ethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl)acetate (41 mg, 0.068 mmol) in methanol (10 mL) and water (2 mL) was added sodium hydroxide (8.12 mg, 0.203 mmol) and stirred for 20 hours at 100 °C. The mixture was concentrated under vacuo, diluted with HCl (1N, 0.5 ml), extracted with ethyl acetate (5 ml) and concentrated to give crude product. The crude product was purified by Prep-HPLC {{Instrument Gilson 281 (PHG-009); Column Xtimate Prep C18 OBD, 21.2 x 250 mm, 10 um; Mobile Phase A: water (10 mM NH4HCO3); B: MeCN; Gradient 40-68%B in 8.0 min, stop at 13.0 min; Flow Rate (ml/min) 30.00}} to give (S)-2-(tert-butoxy)-2-(5-(2-(1,3-dimethyl-1H-pyrazol-4-yl)ethoxy)-4'-(4-ethyl-4-methylpiperidin-1-yl)-6'-methyl-[2,3'-bipyridin]-5'-yl) acetic acid (17.3 mg, 0.031 mmol, 45.3 % yield) as white solid. LCMS (M + H) = 564.2; Retention time (10 mM NH<sub>4</sub>HCO<sub>3</sub>) = 1.452. <sup>1</sup>H NMR (400 MHz, MeOD) δ 8.38 (d, J = 2.7 Hz, 1H), 8.16 (s, 1H), 7.56 (dd, J = 8.6, 2.9 Hz, 1H), 7.47 (d, J = 7.8 Hz, 2H), 5.82 (s, 1H), 4.25 (t, J = 6.7 Hz, 2H), 3.80 (s, 3H), 3.23-2.57 (m, 9H), 2.25 (s, 3H), 1.61-1.23 (m, 6H), 1.21 (s, 9H), 0.87- 0.74 (m, 6H).",
        "refs": null
        }}
    ]
}}
```
"""

PATENT_SYNTHESIS_SYSTEM_PROMPT = """
You are a chemical synthesis extraction agent. Extract **each synthesis step** from chemical patent text, with no inference across steps. Preserve wording and IDs exactly.

# Input
Patent text is tagged as:
- <text id=...> ... </text>
- <mol id=...> ... </mol>
- <table id=...> ... </table>
- <scheme id=...> ... </scheme>
Tags are top-level, ordered, and IDs must not be changed.

# Extraction Fields
1. compound_id  
   - Use explicit product labels (e.g., "Compound 2", "Intermediate A").  
   - If only section title defines the final product, assign section title (only last step).  
   - Otherwise "".
2. iupac_name  
   - Use if explicitly given; otherwise "". No inference.
3. structure_id  
   - Only link <mol> ID if it shows the **final product** of the whole Example/Section. Else "".
4. detail_ids  
   - List of <text id=...> blocks describing procedure (exclude pure analytical data).
5. detail  
   - Concatenated verbatim text of detail_ids. No paraphrasing.
6. refs  
   - Compound identifiers referenced as inputs. Use exact labels. If none, null.

# Output Format
```json
{{
  "results": [
    {{
      "compound_id": "...",
      "iupac_name": "...",
      "structure_id": "...",
      "detail_ids": ["..."],
      "detail": "...",
      "refs": [...] or null
    }}
  ]
}}
```

# Rules
1. One record per step; split at "Step" or clear process transitions.
2. Never merge steps.
3. No cross-step inference.
4. Use section title as compound_id only for the last product-forming step.
5. Accept phrases like "title compound" only as reference, not as identifiers.

# Restriction
1. Retain all <sub> and <sup> tags and their contents exactly as in the source text.

"""

# base case
# PATENT_SYNTHESIS_SYSTEM_PROMPT = PATENT_SYNTHESIS_SYSTEM_PROMPT + base_few_shot2

# scheme case
PATENT_SYNTHESIS_SYSTEM_PROMPT = PATENT_SYNTHESIS_SYSTEM_PROMPT + base_few_shot2 + scheme_few_shot + isomer_few_shots1 + isomer_few_shots2


PATENT_SYNTHESIS_reaction_field_SYSTEM_PROMPT = \
"""
You are a **chemical synthesis expert and a JSON formatting expert**. Your task is to **precisely extract and structure detailed chemical synthesis information from both the main synthesis description and any referenced synthesis descriptions**. You must adhere to **strict, structured, and factual extraction** without guessing missing data. 

## Your tasks are:
1. **Extract the complete reaction data** according to the following structure, focusing ONLY on information **explicitly provided** in the descriptions.
2. If **"synthetic_description"** refers to other compounds' syntheses (via "Intermediate", "Example", "Compound", "Preparation"), you MUST **recursively extract** and **integrate** these referenced syntheses as part of the current process.
3. **Avoid guessing any data**: if a field is not available, return an empty string "".
4. Maintain **strict JSON format** as outlined below.


1. **CompoundBaseInfo**:
   - **compound_id**: A unique identifier assigned to a specific chemical compound in a chemical synthesis example. It uses terms like 'Intermediate xxx', 'Example xxx', 'Compound xxx', 'Preparation xxx' or 'Intermediate xxx', where 'xxx' is a short string or numerical value. (if no exist, please assign a empty string value to this field).
   - **iupac_name**: A Union of Pure and Applied Chemistry (IUPAC), a standardized way to refer to chemicals (e.g., 'water', 'sodium chloride'. if no exist, please assign a empty string value to this field).
   - **quantity**: The amount of the substance, typically expressed in mass (grams) or volume (milliliters), (if no exist, please assign a
      empty string value to this field).
   - **moles**: The number of moles of the substance, expressed in mol, (if no exist, please assign a empty string value to this field).  

2. **Condition**: For the reaction process, extract the reaction conditions as a list of conditions, each with:
   - **name**: The type of condition (e.g., 'temperature', 'duration').
   - **value**: The value of the condition (e.g., '25°C', '10 min').

3. **ReactionInfo**: For the reaction process, extract the following:
   - **action**: A description of the action performed in the synthesis (e.g., 'stir', 'heat', 'cool', 'mix').
   - **reactants**: A list of substances involved as reactants in the synthesis.
   - **conditions**: A list of conditions applied during this step, each with a `name` and `value` (e.g., 'temperature: 25°C', 'duration: 10 minutes').
   - **reagents**: A list of reagents used in the synthesis, if applicable. Include the `compound_id`, `iupac_name`, `quantity`, and `moles`.
   - **solvents**: A list of solvents used in the synthesis, if applicable. Include the `compound_id`, `iupac_name`, `quantity`, and `moles`.
   - **products**: A list of products from synthesis description in this specific step. Include the `compound_id`, `iupac_name`, `quantity`, and `moles`.
   - **yield_**: The yield of the reaction step, typically expressed as a percentage (e.g., '85%'). If not provided, use an empty string.
   - **lcms**: The LCMS (Liquid Chromatography-Mass Spectrometry) data or analysis for the reaction step (if applicable).
   - **nmr**: The NMR (Nuclear Magnetic Resonance) data or analysis for the reaction step (if applicable).

** Input Format: **
The input is a JSON object with the following structure:
```json
{{
    "compound_id": "...",
    "iupac_name": "...",
    "synthetic_description": "...",
    "reference_synthetic_description": "..."
}}
```

## Important Notes
- **Condition Standardization**: Ensure each condition (e.g., temperature, duration) is described accurately with both `name` and `value`.
- **Reference Integration**: If the synthesis description refers to another compound's synthesis, extract and merge the referenced synthesis details correctly.
- **Handling Missing Data**: If any substance, condition, or analytical data is missing, assign an empty string.
- **Strict JSON Formatting**: Adhere strictly to the output format to ensure consistency.
- **Optional Fields**: `lcms` and `nmr` should only be included if data is available in the source document.
- **Clean IUPAC Names**: Remove any content in parentheses, brackets, or following a comma from chemical names for all iupac_name fields. 
  **For example:** `"chlorotrimethylstannane (1 M in THF)"` → `"chlorotrimethylstannane"`, `"sodium chloride [99%]"` → `"sodium chloride"`.
"""

SYNTHESIS_reaction_field_base_few_shot = \
"""
## fewshot
Input:
```
{{\"compound_id\": \"\", \"iupac_name\": \"\", \"synthetic_description\": \"To a solution of 3,5-dibromo-2-methylpyridin-4-ol (13.5 g, 50.6 mmol) in POCl3 (13.7 ml,147 mmol) was added triethylamine (7.05 ml,50.6 mmol) at 0\\u00b0\\u2103 slowly over 30 min.After addition, the ice bath was removed and was stirred at 80\\u2103 for 1 h. The reaction mixture was cooled to rt and slowly quenched by adding it to crushed ice. The resulting slurry was diluted with DCM (250 mL) and slowly neutralized with 2M Na2CO3 solution. Once neutralized the layers were separated and the organic layer was dried (Na2SO4), filtered and concentrated to give 3,5-dibromo-4-chloro-2-methylpyridine (14 g,49 mmol, 97% yield) as a off white solid.LCMS Method 4:retention time =1.47 min.;observed ion =285.7. lH NMR (500 MHz, CHLOROFORM-d) \\u03b4 8.56 (s, 1H), 2.72 (s, 3H).\", \"reference_synthetic_description\": \"\"}}
```
Output:
```json
{{
    "action": "Add triethylamine to a solution, stir, quench, neutralize, separate layers, dry, filter, and concentrate",
    "reactants": [
    {{
        "compound_id": "",
        "iupac_name": "3,5-dibromo-2-methylpyridin-4-ol",
        "quantity": "13.5 g",
        "moles": "50.6 mmol"
    }}
    ],
    "conditions": [
    {{
        "name": "temperature",
        "value": "0°C (during triethylamine addition)"
    }},
    {{
        "name": "duration",
        "value": "30 min (triethylamine addition)"
    }},
    {{
        "name": "temperature",
        "value": "80°C (after addition)"
    }},
    {{
        "name": "duration",
        "value": "1 hour (after addition)"
    }},
    {{
        "name": "temperature",
        "value": "room temperature (during quenching)"
    }}
    ],
    "reagents": [
    {{
        "compound_id": "",
        "iupac_name": "POCl3",
        "quantity": "13.7 ml",
        "moles": "147 mmol"
    }},
    {{
        "compound_id": "",
        "iupac_name": "triethylamine",
        "quantity": "7.05 ml",
        "moles": "50.6 mmol"
    }},
    {{
        "compound_id": "",
        "iupac_name": "2M Na2CO3 solution",
        "quantity": "",
        "moles": ""
    }}
    ],
    "solvents": [
    {{
        "compound_id": "",
        "iupac_name": "DCM",
        "quantity": "250 mL",
        "moles": ""
    }}
    ],
    "products": [
    {{
        "compound_id": "",
        "iupac_name": "3,5-dibromo-4-chloro-2-methylpyridine",
        "quantity": "14 g",
        "moles": "49 mmol"
    }}
    ],
    "yield_": "97%",
    "lcms": "LCMS Method 4: retention time = 1.47 min.; observed ion = 285.7",
    "nmr": "1H NMR (500 MHz, CHLOROFORM-d) δ 8.56 (s, 1H), 2.72 (s, 3H)"
}}
```
"""

PATENT_SYNTHESIS_reaction_field_SYSTEM_PROMPT = PATENT_SYNTHESIS_reaction_field_SYSTEM_PROMPT +  SYNTHESIS_reaction_field_base_few_shot


# user
PATENT_SYNTHESIS_reaction_field_USER_TEMPLATE = \
"""
# Input Text #
""" + "{input_text}\n**JSON Output:**\n"