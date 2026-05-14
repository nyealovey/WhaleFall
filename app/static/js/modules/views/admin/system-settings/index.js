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
    const panels = Array.from(pageRoot.querySelectorAll('[data-system-settings-section]'));
    const panelIds = new Set(panels.map((panel) => panel.id).filter(Boolean));

    if (!navLinks.length || !panels.length) {
        return;
    }

    let activeSectionId = '';

    function resolveSectionId(sectionId) {
        if (sectionId && panelIds.has(sectionId)) {
            return sectionId;
        }
        return panels[0]?.id || '';
    }

    function updateLocationHash(sectionId) {
        if (window.history?.replaceState) {
            window.history.replaceState(null, '', `#${sectionId}`);
        }
    }

    function setActiveSection(sectionId, options = {}) {
        const resolvedSectionId = resolveSectionId(sectionId);
        if (!resolvedSectionId) {
            return;
        }

        if (activeSectionId === resolvedSectionId) {
            if (options.updateHash !== false) {
                updateLocationHash(resolvedSectionId);
            }
            return;
        }

        activeSectionId = resolvedSectionId;

        navLinks.forEach((link) => {
            const isActive = link.dataset.systemSettingsNavLink === resolvedSectionId;
            link.classList.toggle('is-active', isActive);
            link.setAttribute('aria-selected', isActive ? 'true' : 'false');
            if (isActive) {
                link.setAttribute('aria-current', 'location');
            } else {
                link.removeAttribute('aria-current');
            }
        });

        panels.forEach((panel) => {
            const isActive = panel.id === resolvedSectionId;
            panel.classList.toggle('is-active', isActive);
            panel.hidden = !isActive;
            panel.setAttribute('aria-hidden', isActive ? 'false' : 'true');
        });

        if (options.updateHash !== false) {
            updateLocationHash(resolvedSectionId);
        }
    }

    navLinks.forEach((link) => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            setActiveSection(link.dataset.systemSettingsNavLink || '');
        });
    });

    window.addEventListener('hashchange', () => {
        setActiveSection(window.location.hash.replace('#', ''), { updateHash: false });
    });

    setActiveSection(window.location.hash.replace('#', ''), { updateHash: false });
})();
