import gsap from "gsap";
import { PROJECTS } from "./projects";

/**
 * The context under the left lockup: who a piece of work was for, two
 * sentences on what it was, and a link out where one exists.
 *
 * It belongs to the **work**, not the card, so it holds still across all three
 * of a work's plates and changes only when the palette does. That is what
 * makes eighteen pictures read as six projects rather than as a pile.
 *
 * A plain crossfade, deliberately, and not the goo morph six inches to the
 * left of it: that technique welds two blurred words into one silhouette,
 * which is what you want for a name and illegible for a paragraph.
 */
export function createNote(refs, params) {
  const state = { t: 0 };
  let current = null;

  const paint = () => {
    const { box } = refs;
    if (!box) return;
    box.style.opacity = `${state.t * params.noteOpacity}`;
    // A short rise on the way in. Small, because this sits still for three
    // cards at a time and anything larger reads as the page moving.
    box.style.transform = `translateY(${(1 - state.t) * 0.5}em)`;
  };

  const write = (work) => {
    const { label, blurb, link } = refs;
    if (label) label.textContent = `${work.label} · ${work.meta}`;
    if (blurb) blurb.textContent = work.blurb;
    if (link) {
      // Kept in the flow either way would leave a gap under the works that
      // have nothing to link to.
      link.style.display = work.link ? "" : "none";
      if (work.link) {
        link.href = work.link;
        link.textContent = work.linkLabel ?? "Read more";
      }
    }
  };

  const show = (i) => {
    const work = PROJECTS[i]?.work;
    if (!work || work === current) return;
    const first = current === null;
    current = work;
    gsap.killTweensOf(state);

    if (first) {
      write(work);
      state.t = 0;
      paint();
      gsap.to(state, {
        t: 1,
        duration: params.noteFade,
        ease: "power2.out",
        onUpdate: paint,
      });
      return;
    }

    gsap.to(state, {
      t: 0,
      duration: params.noteOut,
      ease: "power2.in",
      onUpdate: paint,
      onComplete: () => {
        write(work);
        gsap.to(state, {
          t: 1,
          duration: params.noteFade,
          ease: "power2.out",
          onUpdate: paint,
        });
      },
    });
  };

  /**
   * Sized and placed off the same figures as the lockup above it, so the two
   * stay one block as the window changes rather than drifting apart.
   *
   * Gone below `narrowAt`, not shrunk. Down there the ring is re-proportioned
   * up and `narrowPosX` pulls it left, so the gutter this sits in is under the
   * front card; and the type is bumped 1.5x in that band because labels cannot
   * shrink like pictures can, which leaves a paragraph about four words to a
   * line. The design already sheds labels a band at a time — this is the same
   * move, one band earlier.
   */
  const style = ({ textK, tight, narrow }) => {
    const { box, label, blurb, link } = refs;
    if (!box) return;

    if (tight || narrow || !params.note) {
      box.style.display = "none";
      return;
    }
    box.style.display = "";

    const bigVw = params.nameSize * textK;
    box.style.left = `${params.metaLeft}vw`;
    box.style.lineHeight = `${params.noteLead}`;
    box.style.top = `calc(50% + ${bigVw * params.noteGap}vw)`;
    box.style.width = `${params.noteWidth}vw`;

    if (label) {
      label.style.fontFamily = `"${params.idxFont}", ui-sans-serif, system-ui, sans-serif`; // prettier-ignore
      label.style.fontSize = `${params.noteLabelSize * textK}vw`;
      // Tracking rather than uppercasing it: these are real names, and
      // "VfOx" is not "VFOX".
      label.style.letterSpacing = "0.07em";
    }
    for (const el of [blurb, link]) {
      if (!el) continue;
      el.style.fontFamily = `"${params.nameFont}", ui-sans-serif, system-ui, sans-serif`; // prettier-ignore
      el.style.fontSize = `${params.noteSize * textK}vw`;
    }
    paint();
  };

  // Reset rather than just stop: a replay re-runs the entry, and the note has
  // to come back in with it instead of already being there.
  const reset = () => {
    gsap.killTweensOf(state);
    current = null;
    state.t = 0;
    paint();
  };

  const dispose = () => gsap.killTweensOf(state);

  return { show, style, reset, dispose };
}
