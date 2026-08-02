# Setting up the Somach GitHub org

## 1. Org profile — the front door

A repo literally named `.github` renders its `profile/README.md` on your org page. This is what a Media Lab admissions reader or an investor sees first.

```bash
gh repo create Somach-Systems-Inc/.github --public --description "Org profile"
git clone https://github.com/Somach-Systems-Inc/.github && cd .github
mkdir -p profile
# copy .github/PROFILE_README.md from this repo to profile/README.md
git add . && git commit -m "Add org profile" && git push
```

## 2. Paper 1 repo

```bash
cd ~/paper1-ear-emg
git init
git add .
git commit -m "Scaffold: outline, config, agent instructions

Volume-conductor model of articulator muscle sources at retroauricular
electrode sites. Method is reciprocity-based (inject at electrodes, read
E-field in muscle compartments) rather than per-source forward solves.

No human subjects, no IRB required."

gh repo create Somach-Systems-Inc/ear-emg-forward-model \
  --public \
  --license apache-2.0 \
  --description "Which speech muscles are visible from behind the ear? A volume-conductor model of articulator sources at retroauricular electrode sites." \
  --source=. --push
```

Add topics so it's findable:
```bash
gh repo edit Somach-Systems-Inc/ear-emg-forward-model \
  --add-topic semg --add-topic silent-speech --add-topic volume-conduction \
  --add-topic simnibs --add-topic ear-eeg --add-topic biosignals
```

## 3. Migrating the capstone — **transfer, don't fork**

Your capstone lives at `CarlKho-Minerva/Somach_sEMG-Silent-Speech` and **that URL is printed in your published capstone document**. GitHub's transfer sets up a permanent redirect from the old URL, so citations keep working. A fork or a fresh repo breaks them.

**On github.com:** repo → Settings → scroll to Danger Zone → **Transfer ownership** → `Somach-Systems-Inc`.

You must be an owner of the org. Stars, issues, and full history come along.

Then rename for consistency:
```bash
gh repo rename semg-silent-speech --repo Somach-Systems-Inc/Somach_sEMG-Silent-Speech
```
(That also redirects.)

### Cleanup pass worth doing after transfer

4,135 files is a lot for a public front door. Consider:

- **Git LFS** for anything over ~50 MB (recorded EMG sessions, model checkpoints). `git lfs migrate import --include="*.csv,*.pth"` — note this rewrites history, so do it deliberately and force-push once.
- **A README that leads with the result**, not the directory tree. The honest 48.9–51.8% CV number and the "here's exactly where $40 runs out" framing is the interesting part.
- **`data/` with a manifest** rather than raw dumps — or push the dataset to Zenodo and get a DOI. Gaddy's dataset on Zenodo is why everyone benchmarks against it; a DOI makes yours citable the same way.
- Keep the CI you already have.

## 4. Repo layout for the org

```
Somach-Systems-Inc/
├── .github                    # org profile
├── semg-silent-speech         # capstone (transferred)
├── ear-emg-forward-model      # Paper 1
└── retroauricular-semg        # Paper 2, once the rig is running
```

**Do not put PLOP here.** That's The Mildly Useful Company — a separate corporation. Mixing repos across two entities muddies the IP story if either company is ever diligenced.

## 5. Licensing

See `LICENSE-NOTE.md`. Short version: **Apache-2.0 for code** (patent grant matters in this field), **CC-BY-4.0 for data and paper text**.
