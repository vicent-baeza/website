// -----------------
// UTILITY FUNCTIONS
// -----------------
function trycatch(trybody, errorhandler, defaultReturn = undefined) {
    try {
        return trybody()
    }
    catch(error) {
        errorhandler(error)
        return defaultReturn
    }
}
function localstorage_errors(trybody) {
    return trycatch(trybody, () => {
        console.warn("LOCAL STORAGE ERRROR!")
    }, '')
}


// ---------
// DARK MODE
// ---------
const darkModeButtons = document.getElementsByClassName('darkmode-button')
if (localstorage_errors(() => localStorage.getItem('lightmode')) == 'enabled') {
    document.body.classList.add('lightmode')
}
for (const darkModeButton of darkModeButtons) {
    darkModeButton.addEventListener('click', () => {
        document.body.classList.toggle('lightmode')
        enabled = document.body.classList.contains('lightmode')
        localstorage_errors(() => {
            localStorage.setItem('lightmode', enabled ? 'enabled' : 'disabled')
        })
    })
}
// add class 'loaded' after 500ms, so that transitions don't trigger on page load
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        document.body.classList.add('loaded')
    }, 500);
})


// --------------
// DYNAMIC FOOTER
// --------------
currentYear = new Date().getFullYear()
document.getElementById('footer-text').textContent = `© ${currentYear} Vicent Baeza`


// -----------------
// FULLSCREEN IMAGES
// -----------------
const fullscreen = document.getElementById('fullscreen')
const fullscreen_img = fullscreen.getElementsByTagName('img')[0]
const fullscreen_card_title = document.getElementById('fullscreen-card-title')
const fullscreen_card_date = document.getElementById('fullscreen-card-date')
const fullscreen_card_content = document.getElementById('fullscreen-card-content')
console.log(fullscreen_img)

// make images fullscreen on click
const card_images = document.querySelectorAll('.card > img')
for(const card_image of card_images) {
    const parent = card_image.parentElement
    const card_title = parent.getElementsByClassName('card-title')[0]
    const card_date = parent.getElementsByClassName('card-date')[0]
    const card_content = parent.getElementsByClassName('img-fullscreen-content')[0]
    console.log(parent)
    console.log(card_title)
    console.log(card_date)
    console.log(card_content)
    parent.onclick = function(e){
        console.log('CLICKED IMAGE')
        fullscreen.style.zIndex = 1000
        fullscreen.style.display = 'flex'
        fullscreen_img.src = card_image.src
        fullscreen_card_title.innerHTML = card_title.innerHTML
        fullscreen_card_date.innerHTML = card_date.innerHTML
        fullscreen_card_content.innerHTML = card_content.innerHTML
        document.body.classList.add("stop-scrolling");
    }
}

// hide fullscreen div on click
fullscreen.onclick = function(e) {
    fullscreen.style.zIndex = -1000
    fullscreen.style.display = 'none'
    document.body.classList.remove("stop-scrolling");
}

