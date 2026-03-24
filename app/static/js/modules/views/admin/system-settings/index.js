(function mountSystemSettingsPage() {
    const pageRoot = document.getElementById('system-settings-page');
    if (!pageRoot) {
        return;
    }

    const navRoot = pageRoot.querySelector('[data-system-settings-nav="true"]');
    if (!navRoot) {
        return;
    }

    const navLinks = Array.from(navRoot.querySelectorAll('[data-system-settings-nav-link]'));
    const sections = navLinks
        .map((link) => document.getElementById(link.dataset.systemSettingsNavLink || ''))
        .filter(Boolean);

    if (!navLinks.length || !sections.length) {
        return;
    }

    let activeSectionId = '';

    function setActiveSection(sectionId) {
        if (!sectionId || activeSectionId === sectionId) {
            return;
        }

        activeSectionId = sectionId;
        navLinks.forEach((link) => {
            const isActive = link.dataset.systemSettingsNavLink === sectionId;
            link.classList.toggle('is-active', isActive);
            if (isActive) {
                link.setAttribute('aria-current', 'location');
            } else {
                link.removeAttribute('aria-current');
            }
        });
    }

    navLinks.forEach((link) => {
        link.addEventListener('click', (event) => {
            const sectionId = link.dataset.systemSettingsNavLink || '';
            const target = document.getElementById(sectionId);
            if (!target) {
                return;
            }

            event.preventDefault();
            setActiveSection(sectionId);
            window.history.replaceState(null, '', `#${sectionId}`);
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start',
            });
        });
    });

    const observer = new IntersectionObserver(
        (entries) => {
            const visibleEntries = entries
                .filter((entry) => entry.isIntersecting)
                .sort((left, right) => right.intersectionRatio - left.intersectionRatio);

            const activeEntry = visibleEntries[0];
            if (activeEntry?.target?.id) {
                setActiveSection(activeEntry.target.id);
            }
        },
        {
            rootMargin: '-18% 0px -52% 0px',
            threshold: [0.2, 0.35, 0.55],
        },
    );

    sections.forEach((section) => observer.observe(section));

    const initialHash = window.location.hash.replace('#', '');
    const initialSection = sections.find((section) => section.id === initialHash) || sections[0];
    if (initialSection) {
        setActiveSection(initialSection.id);
        if (initialHash) {
            window.requestAnimationFrame(() => {
                initialSection.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start',
                });
            });
        }
    }
})();
