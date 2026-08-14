(function () {
'use strict';
var yr = document.getElementById('yr');
if (yr) yr.textContent = String(new Date().getFullYear());
var burger = document.getElementById('burger');
var nav = document.getElementById('nav');
function closeNav() {
if (!nav || !burger) return;
nav.classList.remove('is-open');
burger.setAttribute('aria-expanded', 'false');
burger.setAttribute('aria-label', 'Open menu');
}
if (burger && nav) {
burger.addEventListener('click', function () {
var open = nav.classList.toggle('is-open');
burger.setAttribute('aria-expanded', open ? 'true' : 'false');
burger.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
});
nav.addEventListener('click', function (e) {
if (e.target.tagName === 'A') closeNav();
});
document.addEventListener('keydown', function (e) {
if (e.key === 'Escape') closeNav();
});
window.addEventListener('resize', function () {
if (window.innerWidth > 900) closeNav();
});
}
var hdr = document.getElementById('hdr');
if (hdr) {
var ticking = false;
window.addEventListener('scroll', function () {
if (ticking) return;
ticking = true;
window.requestAnimationFrame(function () {
hdr.classList.toggle('is-stuck', window.scrollY > 8);
ticking = false;
});
}, { passive: true });
}
var form = document.getElementById('bookForm');
if (!form) return;
var ok = document.getElementById('formOk');
var okDetail = document.getElementById('okDetail');
var dateField = document.getElementById('f-date');
if (dateField) {
var t = new Date();
dateField.min = t.getFullYear() + '-' +
String(t.getMonth() + 1).padStart(2, '0') + '-' +
String(t.getDate()).padStart(2, '0');
}
var RULES = {
'f-name': {
test: function (v) { return v.trim().length >= 2; },
msg: 'Please enter your name.'
},
'f-phone': {
test: function (v) { return (v.replace(/\D/g, '').length >= 10); },
msg: 'Please enter a valid phone number (at least 10 digits).'
},
'f-email': {
test: function (v) { return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim()); },
msg: 'Please enter a valid email address.'
},
'f-service': {
test: function (v) { return v !== ''; },
msg: 'Please choose the service you need.'
}
};
function setError(el, message) {
var field = el.closest('.field');
if (!field) return;
var err = field.querySelector('.err');
if (message) {
field.classList.add('is-bad');
el.setAttribute('aria-invalid', 'true');
if (err) err.textContent = message;
} else {
field.classList.remove('is-bad');
el.removeAttribute('aria-invalid');
if (err) err.textContent = '';
}
}
function validateField(id) {
var el = document.getElementById(id);
var rule = RULES[id];
if (!el || !rule) return true;
var pass = rule.test(el.value);
setError(el, pass ? '' : rule.msg);
return pass;
}
Object.keys(RULES).forEach(function (id) {
var el = document.getElementById(id);
if (!el) return;
el.addEventListener('blur', function () { validateField(id); });
el.addEventListener('input', function () {
if (el.closest('.field').classList.contains('is-bad')) validateField(id);
});
el.addEventListener('change', function () {
if (el.closest('.field').classList.contains('is-bad')) validateField(id);
});
});
form.addEventListener('submit', function (e) {
e.preventDefault();
var firstBad = null;
Object.keys(RULES).forEach(function (id) {
if (!validateField(id) && !firstBad) firstBad = document.getElementById(id);
});
if (firstBad) {
if (ok) ok.hidden = true;
firstBad.focus();
return;
}
var name = (document.getElementById('f-name').value || '').trim().split(' ')[0];
var service = document.getElementById('f-service').value;
if (okDetail) {
okDetail.textContent = 'Thanks ' + name + ' — we have your request for "' +
service + '" and will call to confirm your slot.';
}
if (ok) {
ok.hidden = false;
ok.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}
form.reset();
Object.keys(RULES).forEach(function (id) {
var el = document.getElementById(id);
if (el) setError(el, '');
});
});
})();