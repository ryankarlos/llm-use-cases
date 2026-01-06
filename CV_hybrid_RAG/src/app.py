"""Gradio UI for CV Matching Demo - API Mode Only.

Run with: python -m CV_hybrid_RAG.src.app --api-url <API_GATEWAY_URL>
Or set: CV_MATCHER_API_URL=<url>
"""

import argparse
import math
import os
from typing import List, Tuple

import gradio as gr
import pandas as pd
import plotly.graph_objects as go
import requests

API_URL = os.environ.get("CV_MATCHER_API_URL", "")


class APIClient:
    """Client for CV Matcher API."""
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def get(self, path: str) -> dict:
        return requests.get(f"{self.base_url}{path}", timeout=30).json()

    def post(self, path: str, data: dict) -> dict:
        return requests.post(f"{self.base_url}{path}", json=data, timeout=30).json()


class CVMatcherApp:
    def __init__(self, api_url: str):
        if not api_url:
            raise ValueError("API URL required. Set CV_MATCHER_API_URL or use --api-url")
        self.client = APIClient(api_url)
        self.api_url = api_url
        self._load_data()

    def _load_data(self):
        jobs = self.client.get("/jobs")
        self.jobs = jobs.get("details", {})
        self.candidates = self.client.get("/candidates").get("candidates", [])

    def get_job_choices(self) -> List[str]:
        return [f"{v['title']} ({k})" for k, v in self.jobs.items()]

    def get_candidate_choices(self) -> List[str]:
        return [f"{c['name']} ({c['id']})" for c in self.candidates]

    def match_candidates(self, job_sel: str) -> Tuple[pd.DataFrame, go.Figure, go.Figure]:
        if not job_sel:
            return pd.DataFrame(), go.Figure(), go.Figure()
        
        role_id = job_sel.split("(")[-1].rstrip(")")
        result = self.client.post("/match", {"role_id": role_id})
        matches = result.get("matches", [])
        job_title = result.get("job", {}).get("title", role_id)
        
        df = pd.DataFrame([{
            "Rank": i + 1, "Candidate": m["candidate_name"], "Score": f"{m['match_score']:.1f}%",
            "Direct": ", ".join(m.get("direct_matches", [])) or "-",
            "Related": ", ".join(m.get("related_matches", [])) or "-",
            "Gaps": ", ".join(m.get("skill_gaps", [])) or "-"
        } for i, m in enumerate(matches)])
        
        # Bar chart
        bar = go.Figure(go.Bar(
            x=[m["candidate_name"] for m in matches], y=[m["match_score"] for m in matches],
            marker_color=['#2ecc71' if m["match_score"] >= 80 else '#f39c12' if m["match_score"] >= 50 else '#e74c3c' for m in matches],
            text=[f"{m['match_score']:.1f}%" for m in matches], textposition='outside'
        ))
        bar.update_layout(title=f"Match Scores - {job_title}", yaxis_range=[0, 110], template="plotly_white", height=400)
        
        # Radar chart
        categories = self.jobs.get(role_id, {}).get("required_skills", [])[:6]
        radar = go.Figure()
        for i, m in enumerate(matches[:3]):
            cand = next((c for c in self.candidates if c["id"] == m["candidate_id"]), None)
            if cand:
                skills = {s.lower() for s in cand.get("skills", [])}
                vals = [100 if c.lower() in skills else 0 for c in categories] + [100 if categories and categories[0].lower() in skills else 0]
                radar.add_trace(go.Scatterpolar(r=vals, theta=categories + [categories[0]] if categories else [],
                                                 fill='toself', name=m["candidate_name"], opacity=0.6))
        radar.update_layout(polar=dict(radialaxis=dict(range=[0, 100])), title="Skill Coverage (Top 3)", height=400)
        
        return df, bar, radar

    def candidate_details(self, sel: str) -> Tuple[str, go.Figure]:
        if not sel:
            return "Select a candidate", go.Figure()
        cand_id = sel.split("(")[-1].rstrip(")")
        cand = next((c for c in self.candidates if c["id"] == cand_id), None)
        if not cand:
            return "Not found", go.Figure()
        
        info = f"## {cand['name']}\n**Experience:** {cand['experience_years']} years\n**Skills:** {', '.join(cand['skills'])}"
        
        cats = {"Programming": ["Python", "Java", "R", "SQL"], "ML/AI": ["Machine Learning", "Deep Learning", "NLP", "TensorFlow", "PyTorch"],
                "Data": ["Data Analysis", "Statistics", "ETL", "Spark"], "Cloud": ["AWS", "Azure", "Docker", "Kubernetes", "Terraform"]}
        counts = {k: sum(1 for s in cand["skills"] if s in v) for k, v in cats.items()}
        counts["Other"] = len(cand["skills"]) - sum(counts.values())
        counts = {k: v for k, v in counts.items() if v > 0}
        
        fig = go.Figure(go.Pie(labels=list(counts.keys()), values=list(counts.values()), hole=0.4))
        fig.update_layout(title=f"Skills - {cand['name']}", height=350)
        return info, fig

    def compare(self, c1: str, c2: str, job: str) -> Tuple[str, go.Figure]:
        if not all([c1, c2, job]):
            return "Select two candidates and a job", go.Figure()
        
        result = self.client.post("/compare", {
            "candidate1_id": c1.split("(")[-1].rstrip(")"),
            "candidate2_id": c2.split("(")[-1].rstrip(")"),
            "role_id": job.split("(")[-1].rstrip(")")
        })
        
        m1, m2 = result.get("candidate1", {}), result.get("candidate2", {})
        s1, s2 = m1.get("match_score", 0), m2.get("match_score", 0)
        n1, n2 = m1.get("candidate_name", "?"), m2.get("candidate_name", "?")
        winner = "Tie" if abs(s1 - s2) < 1 else (n1 if s1 > s2 else n2)
        
        text = f"## {result.get('job', {}).get('title', '')}\n| | {n1} | {n2} |\n|--|--|--|\n| Score | {s1:.1f}% | {s2:.1f}% |\n| Exp | {m1.get('experience_years', 0)}y | {m2.get('experience_years', 0)}y |\n\n**Winner:** {winner}"
        
        fig = go.Figure([
            go.Bar(name=n1, x=['Score', 'Exp'], y=[s1, m1.get('experience_years', 0) * 10], marker_color='#3498db'),
            go.Bar(name=n2, x=['Score', 'Exp'], y=[s2, m2.get('experience_years', 0) * 10], marker_color='#e74c3c')
        ])
        fig.update_layout(barmode='group', title="Comparison", height=400)
        return text, fig

    def skill_network(self) -> go.Figure:
        skills = {"Python": ["Java", "R"], "Machine Learning": ["Deep Learning", "AI"], "Deep Learning": ["TensorFlow", "PyTorch"],
                  "SQL": ["NoSQL"], "AWS": ["Azure", "GCP"], "Docker": ["Kubernetes"]}
        nodes = set()
        edges = []
        for s, related in skills.items():
            nodes.add(s)
            for r in related:
                nodes.add(r)
                edges.append((s, r))
        
        nodes = list(nodes)
        n = len(nodes)
        x = [math.cos(2 * math.pi * i / n) for i in range(n)]
        y = [math.sin(2 * math.pi * i / n) for i in range(n)]
        pos = {node: (x[i], y[i]) for i, node in enumerate(nodes)}
        
        ex, ey = [], []
        for e in edges:
            ex.extend([pos[e[0]][0], pos[e[1]][0], None])
            ey.extend([pos[e[0]][1], pos[e[1]][1], None])
        
        fig = go.Figure([
            go.Scatter(x=ex, y=ey, mode='lines', line=dict(width=0.5, color='#888'), hoverinfo='none'),
            go.Scatter(x=x, y=y, mode='markers+text', text=nodes, textposition="top center",
                       marker=dict(size=15, color='#3498db'))
        ])
        fig.update_layout(title="Skill Network", showlegend=False, height=500,
                          xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                          yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
        return fig

    def build_ui(self) -> gr.Blocks:
        with gr.Blocks(title="CV Matcher") as app:
            gr.Markdown(f"# 🎯 CV Matcher\n`{self.api_url}`")
            
            with gr.Tabs():
                with gr.TabItem("🔍 Match"):
                    job_dd = gr.Dropdown(choices=self.get_job_choices(), label="Job Role")
                    btn = gr.Button("Match", variant="primary")
                    tbl = gr.Dataframe()
                    with gr.Row():
                        bar = gr.Plot()
                        radar = gr.Plot()
                    btn.click(self.match_candidates, [job_dd], [tbl, bar, radar])
                
                with gr.TabItem("👤 Details"):
                    cand_dd = gr.Dropdown(choices=self.get_candidate_choices(), label="Candidate")
                    btn2 = gr.Button("View", variant="primary")
                    with gr.Row():
                        info = gr.Markdown()
                        pie = gr.Plot()
                    btn2.click(self.candidate_details, [cand_dd], [info, pie])
                
                with gr.TabItem("⚖️ Compare"):
                    with gr.Row():
                        c1 = gr.Dropdown(choices=self.get_candidate_choices(), label="Candidate 1")
                        c2 = gr.Dropdown(choices=self.get_candidate_choices(), label="Candidate 2")
                        j = gr.Dropdown(choices=self.get_job_choices(), label="Job")
                    btn3 = gr.Button("Compare", variant="primary")
                    cmp = gr.Markdown()
                    cmp_chart = gr.Plot()
                    btn3.click(self.compare, [c1, c2, j], [cmp, cmp_chart])
                
                with gr.TabItem("🕸️ Network"):
                    btn4 = gr.Button("Generate", variant="primary")
                    net = gr.Plot()
                    btn4.click(self.skill_network, outputs=[net])
        
        return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=API_URL, help="API Gateway URL")
    args = parser.parse_args()
    
    app = CVMatcherApp(args.api_url)
    app.build_ui().launch(server_name="0.0.0.0", server_port=7860)


if __name__ == "__main__":
    main()
