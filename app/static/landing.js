// Scroll reveal animation
const reveals = document.querySelectorAll('.reveal');

function revealOnScroll() {
    const windowHeight = window.innerHeight;
    const elementVisible = 100;
    
    reveals.forEach(reveal => {
        const elementTop = reveal.getBoundingClientRect().top;
        if (elementTop < windowHeight - elementVisible) {
            reveal.classList.add('active');
        }
    });
}

window.addEventListener('scroll', revealOnScroll);
setTimeout(revealOnScroll, 100);

// Interactive Billing Toggle Switcher
const billingToggle = document.getElementById('billing-toggle');
const labelMonthly = document.getElementById('label-monthly');
const labelAnnual = document.getElementById('label-annual');
const priceStarter = document.getElementById('price-starter');
const pricePro = document.getElementById('price-pro');
const priceEnterprise = document.getElementById('price-enterprise');

if (billingToggle) {
    let isAnnual = false;
    
    billingToggle.addEventListener('click', () => {
        isAnnual = !isAnnual;
        billingToggle.classList.toggle('annual-active', isAnnual);
        labelMonthly.classList.toggle('active', !isAnnual);
        labelAnnual.classList.toggle('active', isAnnual);
        
        if (isAnnual) {
            priceStarter.innerHTML = '$0<span>/year</span>';
            pricePro.innerHTML = '$39<span>/month</span> <small style="font-size:0.75rem; color:var(--status-green); font-weight:700; display:block;">Billed annually ($468/yr)</small>';
            priceEnterprise.innerHTML = '$159<span>/month</span> <small style="font-size:0.75rem; color:var(--status-green); font-weight:700; display:block;">Billed annually ($1,908/yr)</small>';
        } else {
            priceStarter.innerHTML = '$0<span>/month</span>';
            pricePro.innerHTML = '$49<span>/month</span>';
            priceEnterprise.innerHTML = '$199<span>/month</span>';
        }
    });
}
