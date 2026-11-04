# Decisions

## 2026-11-04: FrameShelf-style public README

- Follow FrameShelf's README presentation: centered logo and message, navigation, product preview, feature table, user/developer quick starts, development commands, layout, documentation, feedback, and status/terms. Keep Scaff It-specific claims and download instructions accurate.
- With owner approval, add assets/ containing only the selected light/dark logos (SVG and PNG) and an illustrative project-folder preview (SVG and PNG). Use PNGs in the README to preserve lettering without requiring the viewer's system fonts.
- Keep old concepts, unused variants, full boards, icon handoffs, and working exports in ignored local/. Distinguish newer source branding from the unchanged public 0.1.0 app.

## 2026-11-04: public guidance and local working material

- Keep the essential AI instructions, requirements, decisions, current checkpoint, plans, QA, and useful maintainer documents public. Product Markdown templates stay tracked.
- Put drafts, transcripts, old checkpoint snapshots, and other temporary work in ignored local/. Add explicit ignore patterns for temporary assistant notes/settings and generated test reports; do not blanket-ignore .agent/ or Markdown.
- Keep CHECKPOINT.md concise and current; preserve old working snapshots locally. No currently tracked throwaway documents were found to untrack, and no history rewrite is needed.
- Publish the reviewed palette/UI changes together with this cleanup through a pull request, preserving the required Tests and repository safety check on main.

## 2026-11-04: shared interface and brand palette

- Adopt the supplied cream #F0E8D0, gold #B09050, garnet #A02838, burgundy #6A1828, and ink #200808 palette. The folder tab changes from teal to gold; the selected geometry stays unchanged.
- Use cream on ink for the interactive text menu, gold headings, cream on garnet for action labels, and cream on burgundy for section labels. Use cream surfaces and ink text for light branding. Do not use cream text on gold.
- Keep terminal styling standard-library only, restore terminal settings on exit, and preserve plain output for redirection, NO_COLOR, dumb terminals, and unsupported Windows consoles. Native Windows folder dialogs retain system styling.
- UI code is updated in source; published releases remain unchanged until an authorized build and release.

## 2026-11-04: selected Scaff It branding

- Use the folder mark with a flowing S-shaped ribbon and a small square; round only the square's bottom-right corner. Keep the teal folder tab.
- Keep the existing tagline. Use the headline One project folder. A clear plan for every AI.
- Explain organised project folders and shared plans, decisions, and progress in everyday language. Say AI assistant and project notes in public-facing explanations.
- Store the durable brand guide in docs/developer/BRANDING.md. Current logo, board, PNG, and Windows icon exports remain in ignored local/ for handoff; application integration and release publication are separate work.
- Keep earlier exploration files as reference. The selected branding bundle contains only the current identity.

## 2026-11-04: public Scaff It baseline

- Use Scaff It as the public name, scaff-it as the repository slug, and Scaff It.exe for the Windows app.
- Use the tagline Set up your project. Start building.
- Initialize independent public history from reviewed maintained source. Include no earlier Git database or local recovery material.
- Keep the existing Python architecture, v2 profile format, preview/preservation behavior, and standard-library runtime.
- Use a portable Windows ZIP with patched Python and retained component notices. An initial 0.1.0 release records the actual first public publication.
- Use public/noreply commit attribution. The initial public repository, push, and verified download are owner-authorized; normal future commit/push policy remains ask.
