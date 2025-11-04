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


// -----------
// LOCAL LINKS
// -----------

const protocol = window.location.protocol
if (protocol == 'file:') { // files are local
    
}