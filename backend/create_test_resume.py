"""
Creates a realistic test resume PDF for end-to-end testing.
"""
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import os

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "test_resume.pdf")

def create_resume():
    c = canvas.Canvas(OUTPUT_PATH, pagesize=letter)
    width, height = letter
    y = height - inch  # start 1 inch from top

    def line(text, size=11, bold=False, gap=16):
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        c.drawString(inch, y, text)
        y -= gap

    def divider():
        nonlocal y
        c.setLineWidth(0.5)
        c.line(inch, y + 4, width - inch, y + 4)
        y -= 6

    # Header
    line("Priya Sharma", size=18, bold=True, gap=20)
    line("Full Stack Software Engineer", size=13, gap=14)
    line("priya.sharma@email.com  |  +91-98765-43210  |  linkedin.com/in/priyasharma  |  github.com/priyasharma", size=9, gap=20)
    divider()

    # Summary
    line("PROFESSIONAL SUMMARY", size=12, bold=True, gap=14)
    line("Results-driven Full Stack Engineer with 4+ years of experience building scalable web applications.", gap=13)
    line("Proficient in Python, React, Node.js, and cloud technologies. Delivered features used by 500K+ users.", gap=13)
    line("Strong background in microservices, REST APIs, and CI/CD pipelines.", gap=18)
    divider()

    # Experience
    line("EXPERIENCE", size=12, bold=True, gap=14)
    line("Senior Software Engineer — TechCorp Solutions, Bengaluru", bold=True, gap=13)
    line("July 2022 – Present", size=9, gap=12)
    line("• Architected a Python/FastAPI microservices platform serving 500K+ daily active users.", gap=12)
    line("• Reduced API response latency by 42% through Redis caching and database query optimization.", gap=12)
    line("• Led migration from monolith to microservices, cutting deployment time from 45 min to 8 min.", gap=12)
    line("• Mentored 4 junior engineers; conducted weekly code reviews and pair programming sessions.", gap=16)

    line("Software Engineer — Innovate Labs, Pune", bold=True, gap=13)
    line("June 2020 – June 2022", size=9, gap=12)
    line("• Built React + TypeScript dashboard for real-time analytics, increasing user engagement by 28%.", gap=12)
    line("• Developed RESTful APIs with Django REST Framework integrated with PostgreSQL and Redis.", gap=12)
    line("• Automated CI/CD pipelines using GitHub Actions and Docker, reducing release cycle by 60%.", gap=12)
    line("• Integrated third-party payment gateways (Razorpay, Stripe) processing ₹2Cr+ monthly transactions.", gap=18)
    divider()

    # Education
    line("EDUCATION", size=12, bold=True, gap=14)
    line("B.Tech in Computer Science and Engineering", bold=True, gap=13)
    line("BITS Pilani, Rajasthan  |  2016 – 2020  |  CGPA: 8.7 / 10", size=9, gap=18)
    divider()

    # Skills
    line("SKILLS", size=12, bold=True, gap=14)
    line("Languages:   Python, JavaScript, TypeScript, SQL, Bash", gap=12)
    line("Frontend:    React, Next.js, HTML5, CSS3, Tailwind CSS", gap=12)
    line("Backend:     FastAPI, Django, Node.js, Express.js, REST APIs, GraphQL", gap=12)
    line("Databases:   PostgreSQL, MongoDB, Redis, MySQL", gap=12)
    line("DevOps:      Docker, Kubernetes, GitHub Actions, AWS (EC2, S3, Lambda), Terraform", gap=12)
    line("Tools:       Git, Jira, Postman, Figma, VS Code", gap=18)
    divider()

    # Certifications
    line("CERTIFICATIONS", size=12, bold=True, gap=14)
    line("• AWS Certified Developer – Associate (2023)", gap=12)
    line("• Google Cloud Professional Data Engineer (2022)", gap=12)

    c.save()
    print(f"[OK] Test resume created: {os.path.abspath(OUTPUT_PATH)}")
    return os.path.abspath(OUTPUT_PATH)

if __name__ == "__main__":
    create_resume()
