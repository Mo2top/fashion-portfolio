const projects = [
  {
    title: 'Collection concept',
    category: 'Fashion design',
    description: 'A space for your sketches, inspiration, and collection story.',
  },
  {
    title: 'Editorial story',
    category: 'Art direction',
    description: 'Showcase a visual story through styling and creative direction.',
  },
  {
    title: 'Material exploration',
    category: 'Creative research',
    description: 'Share your experiments with textures, color, and form.',
  },
]

export default function App() {
  return (
    <>
      <a className="skip-link" href="#main">Skip to content</a>
      <header className="site-header container">
        <a className="wordmark" href="#home" aria-label="Portfolio home">Your Name<span> / Portfolio</span></a>
        <nav aria-label="Main navigation">
          <a href="#work">Work</a>
          <a href="#about">About</a>
          <a href="#contact">Contact</a>
        </nav>
      </header>

      <main id="main" className="container">
        <section id="home" className="hero" aria-labelledby="hero-title">
          <p className="eyebrow">Fashion · Design · Creative exploration</p>
          <h1 id="hero-title">Ideas shaped<br />into <em>stories.</em></h1>
          <p className="intro">I'm Your Name, a creative exploring the connection between fashion, identity, and everyday life. Welcome to my portfolio.</p>
          <a className="button" href="#work">Explore my work <span aria-hidden="true">↗</span></a>
        </section>

        <section id="work" className="section" aria-labelledby="work-title">
          <div className="section-heading">
            <h2 id="work-title">Selected work</h2>
            <p>Sample projects · Make these your own</p>
          </div>
          <div className="project-grid">
            {projects.map((project, index) => (
              <article className="project" key={project.title}>
                <div className={`project-art project-art-${index + 1}`} aria-hidden="true">
                  <span>0{index + 1}</span>
                </div>
                <p className="eyebrow">{project.category}</p>
                <h3>{project.title}</h3>
                <p>{project.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="about" className="section about" aria-labelledby="about-title">
          <h2 id="about-title">A little about me</h2>
          <div>
            <p>I find inspiration in the details: a silhouette, an unexpected color, a story waiting to be told.</p>
            <p>Use this space to introduce yourself, your background, and what you love to create. Add your experience, interests, or the kind of collaborations you're looking for.</p>
          </div>
        </section>

        <section id="contact" className="section contact" aria-labelledby="contact-title">
          <p className="eyebrow">Let's connect</p>
          <h2 id="contact-title">Have something<br />in mind?</h2>
          <p>I'd love to hear about your next idea.</p>
          <a className="contact-link" href="mailto:hello@example.com">hello@example.com <span aria-hidden="true">↗</span></a>
        </section>
      </main>

      <footer className="container site-footer">
        <p>© {new Date().getFullYear()} Your Name</p>
        <a href="#home">Back to top ↑</a>
      </footer>
    </>
  )
}
