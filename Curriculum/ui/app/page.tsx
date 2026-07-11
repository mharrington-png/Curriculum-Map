"use client";

import { useEffect, useMemo, useState } from "react";

type Occurrence = {
  skill_id: string; course_id: string; course: string; unit_id: string;
  unit_title: string; priority: "review" | "required" | "extension";
  objective_id: string; objective: string;
  relationship: "prerequisite" | "required" | "method-dependent";
  progression: "introduce" | "reinforce" | "deepen" | "apply";
};
type Skill = {
  skill_id: string; description: string; introduction_status: string;
  first_introduced_course: string | null; inherited_note: string | null;
  courses: string[]; occurrences: Occurrence[];
};

const courses = [
  { id: "M12", label: "Math 12", title: "Intermediate Algebra", tone: "blue" },
  { id: "M21", label: "Math 21", title: "Intermediate Algebra II", tone: "mint" },
  { id: "M22", label: "Math 22", title: "Geometry", tone: "gold" },
  { id: "M31", label: "Math 31", title: "Advanced Algebra", tone: "violet" },
  { id: "M32", label: "Math 32", title: "Trigonometry", tone: "coral" },
  { id: "M49", label: "Math 49", title: "Precalculus with Limits", tone: "navy" },
];
const roleLabel = { introduce: "Introduce", reinforce: "Reinforce", deepen: "Deepen", apply: "Apply" };

export default function Home() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [courseId, setCourseId] = useState<string | null>(null);
  const [objectiveId, setObjectiveId] = useState<string | null>(null);
  const [skillId, setSkillId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [overview, setOverview] = useState(false);

  useEffect(() => { fetch(`${import.meta.env.BASE_URL}data/skill_progressions.json`).then(r => r.json()).then(setSkills); }, []);
  const allOccurrences = useMemo(() => skills.flatMap(s => s.occurrences), [skills]);
  const selectedCourse = courses.find(c => c.id === courseId);
  const courseOccurrences = allOccurrences.filter(o => o.course_id === courseId);
  const objectives = useMemo(() => {
    const map = new Map<string, Occurrence>();
    courseOccurrences.forEach(o => map.set(o.objective_id, o));
    return [...map.values()].sort((a, b) => a.objective_id.localeCompare(b.objective_id));
  }, [courseOccurrences]);
  const selectedObjective = objectives.find(o => o.objective_id === objectiveId);
  const objectiveSkills = skills.filter(s => s.occurrences.some(o => o.objective_id === objectiveId));
  const selectedSkill = skills.find(s => s.skill_id === skillId);
  const searchResults = query.length > 1 ? skills.filter(s => `${s.skill_id} ${s.description}`.toLowerCase().includes(query.toLowerCase())).slice(0, 8) : [];

  const openCourse = (id: string) => { setCourseId(id); setObjectiveId(null); setSkillId(null); setOverview(false); };
  const goHome = () => { setCourseId(null); setObjectiveId(null); setSkillId(null); setOverview(false); };

  return <main>
    <header className="topbar">
      <button className="brand" onClick={goHome}><span className="brandmark">M</span><span>Middlesex Mathematics<small>Curriculum Map</small></span></button>
      <nav><button onClick={() => { goHome(); setOverview(true); }}>Curriculum overview</button><button onClick={goHome}>Courses</button></nav>
      <div className="searchbox">
        <span>⌕</span><input aria-label="Search skills" placeholder="Search a skill…" value={query} onChange={e => setQuery(e.target.value)} />
        {searchResults.length > 0 && <div className="searchresults">{searchResults.map(s => <button key={s.skill_id} onClick={() => { setSkillId(s.skill_id); setQuery(""); setOverview(false); }}>{s.description}<small>{s.skill_id}</small></button>)}</div>}
      </div>
    </header>

    {!courseId && !skillId && !overview && <div className="shell">
      <section className="hero"><p className="eyebrow">Department curriculum</p><h1>Start with a course.<br/><em>See how the learning connects.</em></h1><p>Explore learning objectives, the skills that support them, and how mathematical tools grow across the full course sequence.</p></section>
      <section className="coursegrid">{courses.map(c => {
        const occ = allOccurrences.filter(o => o.course_id === c.id);
        const objectiveCount = new Set(occ.map(o => o.objective_id)).size;
        const skillCount = new Set(occ.map(o => o.skill_id)).size;
        return <button className={`coursecard ${c.tone}`} key={c.id} onClick={() => openCourse(c.id)}><span className="coursecode">{c.label}</span><h2>{c.title}</h2><div className="cardstats"><span><b>{objectiveCount || "—"}</b> objectives</span><span><b>{skillCount || "—"}</b> skills</span></div><span className="open">Open course <b>→</b></span></button>;
      })}</section>
      <button className="overviewcallout" onClick={() => setOverview(true)}><span><b>Zoom out to the full curriculum</b><small>See explicit progression and the carried-forward student toolkit across all six courses.</small></span><b>View curriculum →</b></button>
    </div>}

    {overview && <div className="shell page"><button className="back" onClick={goHome}>← All courses</button><p className="eyebrow">Curriculum overview</p><h1>The student toolkit grows forward.</h1><p className="lede">Skills remain available after they are introduced, even when a later course does not name them explicitly.</p><div className="sequence">{courses.map((c, i) => <button key={c.id} onClick={() => openCourse(c.id)}><span>{i + 1}</span><b>{c.label}</b><small>{c.title}</small></button>)}</div><div className="legendpanel"><h2>How to read the pathway</h2><div className="legend"><span className="dot introduce">I</span> Introduce <span className="dot reinforce">R</span> Reinforce <span className="dot deepen">D</span> Deepen <span className="dot apply">A</span> Apply <span className="carryline"/> Carried forward</div></div></div>}

    {courseId && selectedCourse && !skillId && <div className="shell page">
      <button className="back" onClick={goHome}>← All courses</button><div className="coursehead"><div><p className="eyebrow">{selectedCourse.label}</p><h1>{selectedCourse.title}</h1><p>{objectives.length} learning objectives · {new Set(courseOccurrences.map(o => o.skill_id)).size} supporting skills</p></div><button onClick={() => { setCourseId(null); setOverview(true); }}>View in curriculum →</button></div>
      <div className="coursebody"><section className="objectiveList">{["review","required","extension"].map(priority => {
        const group = objectives.filter(o => o.priority === priority); if (!group.length) return null;
        return <div key={priority}><h2 className={`priority ${priority}`}>{priority}</h2>{group.map(o => <button className={objectiveId === o.objective_id ? "objective active" : "objective"} key={o.objective_id} onClick={() => setObjectiveId(o.objective_id)}><small>{o.unit_title}</small><span>{o.objective}</span><b>→</b></button>)}</div>;
      })}</section>
      <aside className="detail">{selectedObjective ? <><p className="eyebrow">Objective detail</p><code>{selectedObjective.objective_id}</code><h2>{selectedObjective.objective}</h2><p className="muted">Supporting skills</p>{objectiveSkills.map(s => { const o=s.occurrences.find(x=>x.objective_id===objectiveId)!; return <button className="skillrow" key={s.skill_id} onClick={()=>setSkillId(s.skill_id)}><span className={`dot ${o.progression}`}>{roleLabel[o.progression][0]}</span><span>{s.description}<small>{roleLabel[o.progression]} · {o.relationship}</small></span><b>→</b></button>})}</> : <div className="empty"><span>↳</span><h2>Select an objective</h2><p>See its supporting skills and place in the curriculum progression.</p></div>}</aside></div>
    </div>}

    {selectedSkill && <div className="shell page"><button className="back" onClick={() => setSkillId(null)}>← {selectedCourse ? selectedCourse.label : "Back"}</button><p className="eyebrow">Skill explorer</p><code>{selectedSkill.skill_id}</code><h1 className="skilltitle">{selectedSkill.description}</h1><p className="lede">{selectedSkill.introduction_status === "inherited" ? selectedSkill.inherited_note : `First introduced in ${selectedSkill.first_introduced_course}.`} Once established, this skill remains available in the student toolkit.</p>
      <div className="timeline">{courses.map(c => { const items=selectedSkill.occurrences.filter(o=>o.course_id===c.id); const origin=selectedSkill.first_introduced_course; const originIndex=courses.findIndex(x=>x.label===origin); const currentIndex=courses.findIndex(x=>x.id===c.id); const carried=!items.length && (selectedSkill.introduction_status==="inherited" || (originIndex>=0 && currentIndex>originIndex)); return <div className={`timecourse ${items.length?"explicit":carried?"carried":"future"}`} key={c.id}><div className="timehead"><b>{c.label}</b>{carried&&<span>Carried forward</span>}</div>{items.map((o,i)=><button key={`${o.objective_id}-${i}`} onClick={()=>{setCourseId(o.course_id);setObjectiveId(o.objective_id);setSkillId(null)}}><span className={`dot ${o.progression}`}>{roleLabel[o.progression][0]}</span><span><b>{roleLabel[o.progression]}</b><small>{o.objective}</small></span></button>)}</div>})}</div>
    </div>}
  </main>;
}
