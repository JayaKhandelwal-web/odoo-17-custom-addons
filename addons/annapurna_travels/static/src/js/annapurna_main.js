/* Annapurna Travels Custom JavaScript - Bootstrap Compatible */

document.addEventListener('DOMContentLoaded', function() {

    // Initialize all functions
    initUniversalNavigation();
    initScrollEffects();
    initSmoothScrolling();
    initFormValidation();
    initBookingForm();
    initAnimations();
    initScrollToTop();
    initActiveNavLinks();
    initResponsiveFixes();
    initMobileNavigation();

    // Responsive Fixes for Device Compatibility
    function initResponsiveFixes() {
        // Fix hero section height on mobile
        function fixHeroHeight() {
            const heroSection = document.querySelector('.hero-section');
            if (heroSection && window.innerWidth <= 991) {
                const viewportHeight = window.innerHeight;
                heroSection.style.minHeight = viewportHeight + 'px';
            }
        }

        // Fix fleet card buttons overlap
        function fixFleetButtons() {
            const fleetCards = document.querySelectorAll('.fleet-card');
            fleetCards.forEach(card => {
                const buttons = card.querySelectorAll('.btn');
                if (window.innerWidth <= 575) {
                    buttons.forEach(btn => {
                        btn.style.display = 'block';
                        btn.style.width = '100%';
                        btn.style.marginBottom = '0.5rem';
                    });
                } else if (window.innerWidth <= 991) {
                    buttons.forEach(btn => {
                        btn.style.display = 'inline-block';
                        btn.style.width = 'calc(50% - 0.25rem)';
                        btn.style.marginRight = '0.5rem';
                    });
                } else {
                    buttons.forEach(btn => {
                        btn.style.display = 'inline-block';
                        btn.style.width = 'auto';
                        btn.style.marginRight = '0.5rem';
                    });
                }
            });
        }

        // Fix navigation overlap
        function fixNavigationOverlap() {
            const universalNav = document.querySelector('.universal-hero-navigation');
            const mobileNav = document.querySelector('.annapurna-header');

            if (window.innerWidth <= 991) {
                if (universalNav) universalNav.style.display = 'none';
                if (mobileNav) mobileNav.style.display = 'block';
            } else {
                if (universalNav) universalNav.style.display = 'block';
                if (mobileNav) mobileNav.style.display = 'none';
            }
        }

        // Apply fixes on load
        fixHeroHeight();
        fixFleetButtons();
        fixNavigationOverlap();

        // Apply fixes on resize with debounce
        let resizeTimeout;
        window.addEventListener('resize', function() {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(function() {
                fixHeroHeight();
                fixFleetButtons();
                fixNavigationOverlap();
            }, 250);
        });

        // Apply fixes on orientation change
        window.addEventListener('orientationchange', function() {
            setTimeout(function() {
                fixHeroHeight();
                fixFleetButtons();
                fixNavigationOverlap();
            }, 300);
        });
    }

    // Universal Navigation Effects - SIMPLIFIED
    function initUniversalNavigation() {
        const universalNav = document.querySelector('.universal-hero-navigation');

        if (universalNav) {
            let scrollTimeout = null;

            function handleNavScroll() {
                const scrollY = window.scrollY;

                if (scrollTimeout) {
                    clearTimeout(scrollTimeout);
                }

                if (scrollY > 50) {
                    universalNav.classList.add('scrolled');
                } else {
                    universalNav.classList.remove('scrolled');
                }
            }

            handleNavScroll();
            window.addEventListener('scroll', handleNavScroll, { passive: true });
        }

        // ONLY ADD HOVER BEHAVIOR ON DESKTOP - Don't interfere with Bootstrap
        if (window.innerWidth > 992) {
            const heroDropdowns = document.querySelectorAll('.hero-nav-item.dropdown');

            heroDropdowns.forEach(dropdown => {
                const toggle = dropdown.querySelector('.hero-nav-link');

                if (toggle) {
                    // Remove data-bs-toggle to prevent Bootstrap from managing it
                    toggle.removeAttribute('data-bs-toggle');

                    let hideTimeout;

                    dropdown.addEventListener('mouseenter', function() {
                        clearTimeout(hideTimeout);
                        const menu = this.querySelector('.hero-dropdown-menu');
                        if (menu) {
                            menu.classList.add('show');
                        }
                    });

                    dropdown.addEventListener('mouseleave', function() {
                        const menu = this.querySelector('.hero-dropdown-menu');
                        hideTimeout = setTimeout(function() {
                            if (menu) {
                                menu.classList.remove('show');
                            }
                        }, 100);
                    });
                }
            });
        }
    }

    // Active Navigation Links
    function initActiveNavLinks() {
        function updateActiveNavLink() {
            const currentPath = window.location.pathname;
            const navLinks = document.querySelectorAll('.hero-nav-link, .nav-link');

            navLinks.forEach(link => {
                link.classList.remove('active');
                try {
                    const linkPath = new URL(link.href, window.location.origin).pathname;
                    if (currentPath === linkPath || (currentPath.startsWith(linkPath) && linkPath !== '/')) {
                        link.classList.add('active');
                    }
                } catch (e) {
                    // Skip invalid URLs
                }
            });
        }

        updateActiveNavLink();
        window.addEventListener('popstate', updateActiveNavLink);
    }

    // Header scroll effect
    function initScrollEffects() {
        const header = document.querySelector('.annapurna-header .navbar');

        if (header) {
            window.addEventListener('scroll', () => {
                const currentScrollY = window.scrollY;

                if (currentScrollY > 100) {
                    header.classList.add('shadow-sm');
                    header.style.background = 'rgba(255, 255, 255, 0.98)';
                } else {
                    header.classList.remove('shadow-sm');
                    header.style.background = 'rgba(255, 255, 255, 0.95)';
                }
            }, { passive: true });
        }
    }

    // Smooth scrolling
    function initSmoothScrolling() {
        const links = document.querySelectorAll('a[href^="#"]');

        links.forEach(link => {
            link.addEventListener('click', function(e) {
                const targetId = this.getAttribute('href');
                if (targetId === '#' || targetId.length <= 1) return;

                const targetElement = document.querySelector(targetId);

                if (targetElement) {
                    e.preventDefault();

                    const navHeight = window.innerWidth > 991 ?
                        (document.querySelector('.universal-hero-navigation') ? 120 : 80) :
                        (document.querySelector('.annapurna-header') ?
                        document.querySelector('.annapurna-header').offsetHeight : 60);

                    const targetPosition = targetElement.offsetTop - navHeight;

                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });

                    // Close mobile menu if open
                    const navbarCollapse = document.querySelector('.navbar-collapse');
                    if (navbarCollapse && navbarCollapse.classList.contains('show')) {
                        const bsCollapse = bootstrap.Collapse.getInstance(navbarCollapse);
                        if (bsCollapse) {
                            bsCollapse.hide();
                        }
                    }
                }
            });
        });
    }

    // Enhanced Mobile Navigation
    function initMobileNavigation() {
        const navbarCollapse = document.querySelector('.navbar-collapse');

        if (navbarCollapse) {
            const navLinks = document.querySelectorAll('.navbar-nav .nav-link:not(.dropdown-toggle)');
            navLinks.forEach(link => {
                link.addEventListener('click', function() {
                    if (navbarCollapse.classList.contains('show')) {
                        const bsCollapse = bootstrap.Collapse.getInstance(navbarCollapse);
                        if (bsCollapse) {
                            bsCollapse.hide();
                        }
                    }
                });
            });
        }
    }

    // Form validation
    function initFormValidation() {
        const forms = document.querySelectorAll('.needs-validation');

        Array.from(forms).forEach(form => {
            form.addEventListener('submit', function(event) {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();

                    const firstInvalid = form.querySelector(':invalid');
                    if (firstInvalid) {
                        firstInvalid.focus();
                    }
                }

                form.classList.add('was-validated');
            });

            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                input.addEventListener('blur', function() {
                    if (this.checkValidity()) {
                        this.classList.remove('is-invalid');
                        this.classList.add('is-valid');
                    } else {
                        this.classList.remove('is-valid');
                        this.classList.add('is-invalid');
                    }
                });
            });
        });
    }

    // Booking form functionality
    function initBookingForm() {
        const bookingForm = document.getElementById('bookingForm');
        if (!bookingForm) return;

        const pickupDateInput = document.getElementById('pickup_date');
        const returnDateInput = document.getElementById('return_date');
        const isRoundTripCheckbox = document.getElementById('is_round_trip');
        const passengerCountInput = document.getElementById('passenger_count');
        const availabilityDiv = document.getElementById('bus_availability');

        if (pickupDateInput) {
            const today = new Date().toISOString().slice(0, 16);
            pickupDateInput.min = today;
        }

        if (isRoundTripCheckbox && returnDateInput) {
            const returnLabel = document.querySelector('label[for="return_date"]');

            isRoundTripCheckbox.addEventListener('change', function() {
                if (this.checked) {
                    returnDateInput.style.display = 'block';
                    if (returnLabel) returnLabel.style.display = 'block';
                    returnDateInput.required = true;
                } else {
                    returnDateInput.style.display = 'none';
                    if (returnLabel) returnLabel.style.display = 'none';
                    returnDateInput.required = false;
                    returnDateInput.value = '';
                }
            });
        }

        if (pickupDateInput && returnDateInput) {
            pickupDateInput.addEventListener('change', function() {
                returnDateInput.min = this.value;
                if (returnDateInput.value && returnDateInput.value <= this.value) {
                    returnDateInput.value = '';
                }
            });
        }

        function checkAvailability() {
            if (!pickupDateInput || !pickupDateInput.value || !passengerCountInput || !passengerCountInput.value) return;

            const pickupDate = pickupDateInput.value;
            const returnDate = returnDateInput ? returnDateInput.value : '';
            const passengerCount = passengerCountInput.value;

            if (availabilityDiv) {
                availabilityDiv.innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
            }

            fetch('/booking/check-availability', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        pickup_date: pickupDate,
                        return_date: returnDate,
                        passenger_count: passengerCount
                    }
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.result && availabilityDiv) {
                    if (data.result.available) {
                        availabilityDiv.innerHTML = `
                            <div class="alert alert-success">
                                <i class="fas fa-check-circle me-2"></i>
                                ${data.result.buses.length} buses available for your dates!
                            </div>
                        `;
                    } else {
                        availabilityDiv.innerHTML = `
                            <div class="alert alert-warning">
                                <i class="fas fa-exclamation-triangle me-2"></i>
                                No buses available for the selected dates. Please choose different dates.
                            </div>
                        `;
                    }
                }
            })
            .catch(error => {
                console.error('Error checking availability:', error);
                if (availabilityDiv) {
                    availabilityDiv.innerHTML = `
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            Unable to check availability. Please submit your request and we'll confirm availability.
                        </div>
                    `;
                }
            });
        }

        let availabilityTimeout;
        function debouncedAvailabilityCheck() {
            clearTimeout(availabilityTimeout);
            availabilityTimeout = setTimeout(checkAvailability, 500);
        }

        if (pickupDateInput) {
            pickupDateInput.addEventListener('change', debouncedAvailabilityCheck);
        }
        if (returnDateInput) {
            returnDateInput.addEventListener('change', debouncedAvailabilityCheck);
        }
        if (passengerCountInput) {
            passengerCountInput.addEventListener('change', debouncedAvailabilityCheck);
        }

        window.nextStep = function(step) {
            const currentStep = document.querySelector('.form-step.active');
            const nextStep = document.getElementById('step' + step);

            if (currentStep && nextStep) {
                const currentInputs = currentStep.querySelectorAll('input[required], select[required]');
                let isValid = true;

                currentInputs.forEach(input => {
                    if (!input.value.trim()) {
                        input.classList.add('is-invalid');
                        isValid = false;
                    } else {
                        input.classList.remove('is-invalid');
                    }
                });

                if (isValid) {
                    currentStep.classList.remove('active');
                    nextStep.classList.add('active');
                    updateBookingSummary();
                }
            }
        };

        window.prevStep = function(step) {
            const currentStep = document.querySelector('.form-step.active');
            const prevStep = document.getElementById('step' + step);

            if (currentStep && prevStep) {
                currentStep.classList.remove('active');
                prevStep.classList.add('active');
            }
        };

        function updateBookingSummary() {
            const serviceSelect = document.getElementById('service_type_id');
            const pickupInput = document.getElementById('pickup_location');
            const dropInput = document.getElementById('drop_location');
            const dateInput = document.getElementById('pickup_date');
            const passengersInput = document.getElementById('passenger_count');

            if (serviceSelect && document.getElementById('summary_service')) {
                const summaryService = document.getElementById('summary_service');
                summaryService.textContent = serviceSelect.value ?
                    serviceSelect.options[serviceSelect.selectedIndex].text : 'Not selected';
            }

            if (pickupInput && document.getElementById('summary_pickup')) {
                document.getElementById('summary_pickup').textContent = pickupInput.value || 'Not specified';
            }

            if (dropInput && document.getElementById('summary_drop')) {
                document.getElementById('summary_drop').textContent = dropInput.value || 'Not specified';
            }

            if (dateInput && document.getElementById('summary_date')) {
                if (dateInput.value) {
                    const date = new Date(dateInput.value);
                    document.getElementById('summary_date').textContent =
                        date.toLocaleDateString() + ' at ' + date.toLocaleTimeString();
                } else {
                    document.getElementById('summary_date').textContent = 'Not selected';
                }
            }

            if (passengersInput && document.getElementById('summary_passengers')) {
                document.getElementById('summary_passengers').textContent = passengersInput.value || '1';
            }
        }

        updateBookingSummary();

        ['service_type_id', 'pickup_location', 'drop_location', 'pickup_date', 'passenger_count'].forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', updateBookingSummary);
                element.addEventListener('input', updateBookingSummary);
            }
        });
    }

    // Animation on scroll
    function initAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                    entry.target.classList.add('animate-fade-up');
                }
            });
        }, observerOptions);

        const elementsToAnimate = document.querySelectorAll(
            '.service-card, .fleet-card, .tour-card, .testimonial-card, .feature-item, .why-choose-item'
        );

        elementsToAnimate.forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(30px)';
            el.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
            observer.observe(el);
        });
    }

    // Scroll to top button
    function initScrollToTop() {
        let scrollToTopBtn = document.querySelector('.scroll-to-top');

        if (!scrollToTopBtn) {
            scrollToTopBtn = document.createElement('button');
            scrollToTopBtn.className = 'scroll-to-top';
            scrollToTopBtn.innerHTML = '<i class="fas fa-chevron-up"></i>';
            scrollToTopBtn.setAttribute('aria-label', 'Scroll to top');
            document.body.appendChild(scrollToTopBtn);
        }

        function toggleScrollToTop() {
            if (window.scrollY > 300) {
                scrollToTopBtn.style.display = 'flex';
                scrollToTopBtn.classList.add('show');
            } else {
                scrollToTopBtn.style.display = 'none';
                scrollToTopBtn.classList.remove('show');
            }
        }

        window.addEventListener('scroll', toggleScrollToTop, { passive: true });

        scrollToTopBtn.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });

        toggleScrollToTop();
    }

    // Fleet filter functionality
    const fleetFilters = document.querySelectorAll('.filter-btn');
    if (fleetFilters.length > 0) {
        fleetFilters.forEach(btn => {
            btn.addEventListener('click', function() {
                fleetFilters.forEach(b => b.classList.remove('active'));
                this.classList.add('active');

                const category = this.getAttribute('data-category');
                const fleetCards = document.querySelectorAll('[data-category]');
                let visibleCount = 0;

                fleetCards.forEach(card => {
                    const cardCategory = card.getAttribute('data-category');

                    if (category === 'all' || cardCategory === category) {
                        card.style.display = 'block';
                        visibleCount++;
                    } else {
                        card.style.display = 'none';
                    }
                });

                const noResults = document.getElementById('noResults');
                if (noResults) {
                    noResults.style.display = visibleCount === 0 ? 'block' : 'none';
                }
            });
        });
    }

    // Contact form handling
    const contactForm = document.getElementById('contactForm');
    if (contactForm) {
        contactForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;

            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Sending...';
            submitBtn.disabled = true;

            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Thank you for your message! We will get back to you soon.', 'success');
                    this.reset();
                } else {
                    showNotification('There was an error sending your message. Please try again.', 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('There was an error sending your message. Please try again.', 'danger');
            })
            .finally(() => {
                submitBtn.innerHTML = originalBtnText;
                submitBtn.disabled = false;
            });
        });
    }

    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.forEach(function (tooltipTriggerEl) {
            try {
                new bootstrap.Tooltip(tooltipTriggerEl);
            } catch (e) {
                console.warn('Tooltip initialization failed:', e);
            }
        });
    }

    // Auto-hide alerts
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-20px)';
            setTimeout(() => {
                if (alert.parentElement) {
                    alert.remove();
                }
            }, 300);
        }, 5000);
    });

    // Image lazy loading
    const images = document.querySelectorAll('img[data-src]');
    if (images.length > 0) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });

        images.forEach(img => imageObserver.observe(img));
    }

    // Phone number formatting
    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    phoneInputs.forEach(input => {
        input.addEventListener('input', function() {
            let value = this.value.replace(/\D/g, '');

            if (value.length > 10) {
                value = value.substring(0, 10);
            }

            if (value.length >= 6) {
                value = value.replace(/(\d{3})(\d{3})(\d{4})/, '$1-$2-$3');
            } else if (value.length >= 3) {
                value = value.replace(/(\d{3})(\d{1,3})/, '$1-$2');
            }

            this.value = value;
        });
    });

    // Service card hover effects
    const serviceCards = document.querySelectorAll('.service-card');
    serviceCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // Fleet card hover effects
    const fleetCards = document.querySelectorAll('.fleet-card');
    fleetCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

});

// Global utility functions
window.AnnapurnaUtils = {
    scrollToElement: function(elementId, offset = 120) {
        const element = document.getElementById(elementId);
        if (element) {
            const elementPosition = element.getBoundingClientRect().top + window.pageYOffset;
            window.scrollTo({
                top: elementPosition - offset,
                behavior: 'smooth'
            });
        }
    },

    formatCurrency: function(amount) {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            minimumFractionDigits: 0
        }).format(amount);
    }
};

// Utility functions
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} notification position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR'
    }).format(amount);
}

function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function validatePhone(phone) {
    const phoneRegex = /^[6-9]\d{9}$/;
    return phoneRegex.test(phone.replace(/\D/g, ''));
}