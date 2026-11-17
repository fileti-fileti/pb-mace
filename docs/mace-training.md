# MACE training and test

Fixed 2026-11-17, before any training job (CLAUDE.md, Hard rules; ADR-0013). Owner's
answers: "A. OK. B. OK. C. OK" (foundation copy, this doc), "Consolidado, entra como está",
and "Tudo, ok" to the agent's proposals below (200 epochs, one seed, 24 h jobs with
automatic restart, descriptive test). The agent's reasons are kept next to each choice.

## Question
How large are the energy and force errors, on the held-out test split of `consolidado/`,
of a MACE model fine-tuned on its training split (overall, per system and per element)?
Whether the model is good enough for its purpose is decided by the MLMD vs AIMD RDF
comparison (`docs/rdf-mlmd-vs-aimd.md`), not here.

## Design
**Data**: `data/consolidado/`, copied from the owner's Mac and checked against
`data/consolidado.sha256` (the sha256 list of the journal entry of 2026-11-17). From its
`MANIFEST.txt`: `train.xyz` 2554, `valid.xyz` 320, `test.xyz` 173 frames; `REF_energy` /
`REF_forces` (eV, eV/Å); labels qz (700/70); split by groups (20 consecutive AIMD frames;
event windows), stratified by `config_type`, seed 2026. No stress/virial. Contains Na.
Used as is, with its own train / valid / test split (owner).

**Starting point**: the owner's legacy model `pb_t2A2` (ADR-0008, read-only):
`/scratch/acmes/eudes.fileti3/projects/pb/treino_v1/config_pb_t2A2.yaml`, job script
`treino_t2A2.sbatch`, log `MACE_models/pb_t2A2_run-1.log` (MACE 0.3.15, CUDA 12.1).
It was trained without Na (atomic numbers 1, 6, 7, 8, 26), so it cannot run the reference
systems; only its setup is reused.

**Config**: `configs/mace/pb_mace_v1.yaml` (`mace_run_train` YAML):

| Key | pb_t2A2 (legacy) | This model | Why |
|---|---|---|---|
| `foundation_model` | `zncl2/mace_sr/training/mace_mp_small.model` | `data/foundation/mace_mp_small.model` | same file (sha256 in `data/foundation/SHA256SUMS`); no dependency on another project |
| `train_file`, `valid_file` | `data_t2/{train,valid}_A2.xyz` | `data/consolidado/{train,valid}.xyz` | new dataset (with Na), split by groups |
| `test_file` | none | none | test evaluated once, after the model is fixed (below) |
| `energy_key`, `forces_key` | `REF_energy`, `REF_forces` | same | |
| `E0s` | `average` | `average` | see E0s note |
| `loss`; `energy_weight`; `forces_weight`; `stress_weight` | `weighted`; 1.0; 100.0; 0.0 | same | |
| `lr`; `batch_size`; `valid_batch_size` | 0.0002; 2; 2 | same | |
| `max_num_epochs`; `patience` | 300; 40 | 200; 40 | counted in optimizer steps (batch 2): pb_t2A2 made 559 steps per epoch, about 168k in 300 epochs, and its last validation improvement was at epoch 281 (its saved checkpoint), about 157k steps; `train.xyz` gives 1277 steps per epoch, so 200 epochs are about 255k steps. MACE saves a checkpoint only when the validation loss improves, so the final model is the best one on `valid.xyz` and the epoch limit only caps the cost |
| `r_max` | 6.0 | 6.0 | the foundation model's cutoff |
| `ema`; `ema_decay`; `amsgrad` | true; 0.99; true | same | |
| `default_dtype` | float64 | float64 | |
| `multiheads_finetuning`; `enable_cueq` | False; False | same | cuequivariance is not installed in `mace_env` (legacy logs) |
| `seed` | 1 | 1 (one model) | fine-tuning starts every seed from the same foundation weights, so seeds differ mostly in data order: small spread and a weak committee for 1× the cost. More seeds later make a new claim |
| `restart_latest` | true | true | a job cut by the wall time continues in the next one |

**E0s note**: with `average`, MACE fits E0s by least squares. In the legacy dataset the
C:N (cyanide) and O:H (water) counts were in fixed ratios, so the fit could not separate
them: the pb_t2A2 log gives E0(C) = E0(N) and E0(H) = 2·E0(O). Any least-squares solution
then gives each training frame the same total E0, so training is unaffected, but the
individual E0s carry no physical meaning. To check on `consolidado/` (Na included) when it
reaches SDumont.

**Filtering**: none. No frame is removed using a model's residuals (pb_t2A2 removed frames,
validation included, by the residual of the previous model, which makes its validation
error optimistic).

**Compute**: `sequana_gpu`, 1 GPU, `-c 12`, `--exclude=sdumont8042` (owner: the node failed
the owner's runs). Jobs of 24 h; a job cut by the wall time resubmits itself and continues
with `restart_latest`, at most 2 resubmissions. Expected length: pb_t2A2 took about 115 s
per epoch for 316 908 training + 33 626 validation atoms (9 h 40 min for 300 epochs);
if `consolidado/` frames have a similar mean size (2.3× the frames), 200 epochs take about
15 h. Recomputed from the atom count when the data are on SDumont, and measured by the
smoke run.

**Fair comparison**: `valid.xyz` (training side) is the only set used for early stopping
and checkpoint choice; `test.xyz` is evaluated once, with `mace.cli.eval_configs`, after
the model is fixed, and never informs a choice.

## Reading rule (fixed 2026-11-17, before any training job)
- Metrics: RMSE and MAE of forces (meV/Å) and of energy (meV/atom) on `test.xyz`,
  overall, per `config_type` and per element, computed by one script in `src/` (written
  and tested before the test evaluation) from the `eval_configs` output.
- No threshold (owner's option (b), 2026-11-17): the claim reports the errors without a
  yes/no verdict. The yes/no on the model's fitness for the MLMD is the RDF claim of
  `docs/rdf-mlmd-vs-aimd.md`, fixed before any MLMD.
- Claim: `docs/claims.md` ID-1 (pending, descriptive).

## How to run
1. Dataset: `data/consolidado/` from the owner's Mac; `scripts/prep_mace_train.py`
   verifies it against `data/consolidado.sha256` (and the foundation against
   `data/foundation/SHA256SUMS`) every time it prepares a run.
2. Prepare (login node, clean tree): `python3 scripts/prep_mace_train.py
   configs/mace/pb_mace_v1.yaml --partition sequana_gpu --exclude sdumont8042` writes
   `runs/<name>/` with `config.yaml` (absolute data paths), `job.sbatch` (env from
   `configs/machines/sdumont.yaml`) and `run_info.json` (commit, checksums).
3. Smoke run (toy, exempt from the reading rule; ask first): the same config with
   `--epochs 2 --max-chain 0 --partition sequana_gpu_dev --time 00:30:00 --name <smoke name>`:
   checks the config with Na, GPU memory and seconds per epoch.
4. Training (ask first): `cd runs/<name> && sbatch job.sbatch`.
5. Test (after the model is fixed): `eval_configs` on `test.xyz`, then the metrics script.

## Results
- None yet.
