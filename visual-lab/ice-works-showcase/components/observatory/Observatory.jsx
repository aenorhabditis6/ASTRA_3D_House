"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { projects } from "./projects";
import { vertexShader, fragmentShader } from "./shader";
import "./observatory.css";

function Planet({ index, strength, paused, onError }) {
  const host = useRef(null);
  const live = useRef({ index, strength, paused });
  useEffect(() => {
    live.current = { index, strength, paused };
  }, [index, strength, paused]);
  useEffect(() => {
    const container = host.current;
    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    } catch {
      onError(true);
      return;
    }
    container.appendChild(renderer.domElement);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
    const uniforms = {
      resolution: { value: new THREE.Vector2() },
      time: { value: 0 },
      mode: { value: 0 },
      strength: { value: 1 },
      tint: { value: new THREE.Vector3(...projects[0].rgb) },
      pointer: { value: new THREE.Vector2() },
    };
    const material = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms,
    });
    const geometry = new THREE.PlaneGeometry(2, 2);
    const scene = new THREE.Scene();
    scene.add(new THREE.Mesh(geometry, material));
    const camera = new THREE.Camera();
    const resize = new ResizeObserver(() => {
      renderer.setSize(container.clientWidth, container.clientHeight);
      renderer.getDrawingBufferSize(uniforms.resolution.value);
    });
    resize.observe(container);
    const move = (event) => {
      const b = container.getBoundingClientRect();
      uniforms.pointer.value.set(
        (event.clientX - b.left) / b.width - 0.5,
        0.5 - (event.clientY - b.top) / b.height,
      );
    };
    container.addEventListener("pointermove", move);
    let last = performance.now();
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    renderer.setAnimationLoop((now) => {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      const state = live.current;
      if (!state.paused && !reduce.matches && !document.hidden)
        uniforms.time.value += dt;
      uniforms.mode.value = state.index;
      uniforms.strength.value = state.strength;
      uniforms.tint.value.set(...projects[state.index].rgb);
      renderer.render(scene, camera);
    });
    return () => {
      resize.disconnect();
      container.removeEventListener("pointermove", move);
      renderer.setAnimationLoop(null);
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
    };
  }, [onError]);
  return <div ref={host} className="planet-renderer" aria-hidden="true" />;
}

export default function Observatory() {
  const [index, setIndex] = useState(0);
  const [strength, setStrength] = useState(1);
  const [paused, setPaused] = useState(false);
  const [details, setDetails] = useState(false);
  const [error, setError] = useState(false);
  const dialog = useRef(null);
  const returnFocus = useRef(null);
  const project = projects[index];
  const select = (i) => {
    setIndex((i + projects.length) % projects.length);
    setStrength(1);
  };
  useEffect(() => {
    if (details) dialog.current?.showModal();
    else dialog.current?.close();
  }, [details]);
  const close = () => {
    setDetails(false);
    returnFocus.current?.focus();
  };
  return (
    <main className="observatory" style={{ "--accent": project.color }}>
      <header className="obs-header">
        <a
          href="#"
          className="identity"
          aria-label="Tina Shen home"
          onClick={(e) => {
            e.preventDefault();
            select(0);
          }}
        >
          <span className="identity-mark">✳</span>
          <span>
            TINA SHEN
            <span className="identity-sub">A PERSONAL OBSERVATORY</span>
          </span>
        </a>
        <span className="header-note">
          PHYSICS / MATHEMATICS / MAKING THINGS
        </span>
        <a
          className="about-link"
          href="https://www.linkedin.com/in/tinashen26/"
          target="_blank"
          rel="noreferrer"
        >
          About Tina ↗
        </a>
      </header>
      <section className="obs-intro">
        <div>
          <p className="eyebrow">
            <span className="status-dot" /> FIVE WORLDS, ONE CURIOUS MIND
          </p>
          <h1>
            Making sense
            <br />
            of the <em>invisible.</em>
          </h1>
        </div>
        <p className="intro-note">
          I’m Tina. I study physics and applied math,
          <br className="desktop-break" /> and build things at their edges.
          <br />
          <span>Explore a few worlds I’ve worked on.</span>
        </p>
      </section>
      <section
        className="workspace"
        aria-label="Interactive research observatory"
      >
        <nav className="project-nav" aria-label="Choose a project">
          <p className="rail-label">SELECTED EXPLORATIONS</p>
          {projects.map((p, i) => (
            <button
              key={p.id}
              className={`project-item ${index === i ? "selected" : ""}`}
              aria-pressed={index === i}
              onClick={() => select(i)}
            >
              <span className="project-number">0{i + 1}</span>
              <span>
                <span className="project-name">{p.name}</span>
                <span className="project-kind">{p.category}</span>
              </span>
              <span className="project-indicator">
                {index === i ? "↗" : "·"}
              </span>
            </button>
          ))}
          <p className="rail-foot">
            From planetary atmospheres
            <br />
            to the worlds inside an image.
          </p>
        </nav>
        <div
          className="planet-stage"
          tabIndex={0}
          role="group"
          aria-label={`${project.name} planet. Use left and right arrow keys to change projects.`}
          onKeyDown={(e) => {
            if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
              e.preventDefault();
              select(index + (e.key === "ArrowRight" ? 1 : -1));
            }
          }}
        >
          <div className="stage-top">
            <span>{project.coordinates}</span>
            <span className="live-label">
              {paused ? "STILL FRAME" : "PROCEDURAL / LIVE"}
            </span>
          </div>
          <Planet
            index={index}
            strength={strength}
            paused={paused}
            onError={setError}
          />
          {error && (
            <div className="webgl-fallback">
              <div className="fallback-planet" />
              <p>WebGL is unavailable. Explore the projects using the list.</p>
            </div>
          )}
          <span className="axis-label">{project.symbol}</span>
          <div className="stage-bottom">
            <button
              onClick={() => setPaused(!paused)}
              aria-label={paused ? "Resume animation" : "Pause animation"}
            >
              {paused ? "▷ RESUME" : "Ⅱ PAUSE"}
            </button>
            <span>ARTISTIC MODEL · NOT SIMULATION DATA</span>
            <div>
              <button
                onClick={() => select(index - 1)}
                aria-label="Previous project"
              >
                ←
              </button>
              <button
                onClick={() => select(index + 1)}
                aria-label="Next project"
              >
                →
              </button>
            </div>
          </div>
        </div>
        <aside className="project-summary" key={project.id}>
          <p className="eyebrow">{project.category}</p>
          <h2>
            {project.title.split("\n").map((line, i) => (
              <span key={line}>
                {i > 0 && <br />}
                {line}
              </span>
            ))}
          </h2>
          <p className="project-org">{project.org}</p>
          <div className="project-facts">
            <span>{project.role}</span>
            <span>{project.year}</span>
          </div>
          <p className="project-description">{project.description}</p>
          <button
            className="explore-button"
            onClick={(e) => {
              returnFocus.current = e.currentTarget;
              setDetails(true);
            }}
          >
            Open field notes <span>↗</span>
          </button>
          <div className="visual-control">
            <label htmlFor="intensity">
              {project.control}
              <output>{strength.toFixed(1)}×</output>
            </label>
            <input
              id="intensity"
              type="range"
              min="0.3"
              max="2"
              step="0.1"
              value={strength}
              onChange={(e) => setStrength(Number(e.target.value))}
            />
            <p>Change the illustration. Follow your curiosity.</p>
          </div>
        </aside>
      </section>
      <footer className="obs-footer">
        <span>
          Xinming (Tina) Shen{" "}
          <span className="muted">/ Physics & Applied Mathematics, JHU</span>
        </span>
        <span>
          RESEARCH IS A WAY OF SEEING <span className="footer-star">✳</span>
        </span>
      </footer>
      <dialog
        ref={dialog}
        className="field-dialog"
        onCancel={close}
        onClick={(e) => {
          if (e.target === e.currentTarget) close();
        }}
        onClose={() => setDetails(false)}
      >
        <div className="dialog-heading">
          <p className="eyebrow">FIELD NOTES / 0{index + 1}</p>
          <button onClick={close} aria-label="Close field notes">
            ✕
          </button>
        </div>
        <h2>{project.name}</h2>
        <p className="project-org">
          {project.org} · {project.year}
        </p>
        <p>{project.description}</p>
        <div className="tags">
          {project.tags.map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
        </div>
        <h3>Behind this planet</h3>
        <p>{project.note}</p>
        {project.link && (
          <a
            className="explore-button"
            href={project.link}
            target="_blank"
            rel="noreferrer"
          >
            {project.linkLabel} ↗
          </a>
        )}
        <small>
          Experience descriptions adapted from Tina’s CV. All planet
          illustrations are original procedural artwork.
        </small>
      </dialog>
    </main>
  );
}
