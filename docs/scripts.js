// -----------------
// UTILITY FUNCTIONS
// -----------------
start_time = performance.now()
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
const card_images = document.querySelectorAll('.card.cursor-pointer > img')
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
        document.body.classList.add("stop-scrolling")
    }
}

// hide fullscreen div on click
fullscreen.onclick = function(e) {
    fullscreen.style.zIndex = -1000
    fullscreen.style.display = 'none'
    document.body.classList.remove("stop-scrolling")
}


// --------------
// SEARCH DIAGRAM
// --------------
const search_button = document.getElementById('search-button')
const search_bg = document.getElementById('search-bg')
const search_div = document.getElementById('search-div')
const search_textbox = document.getElementById('search-textbox')
const search_options_div = document.getElementById('search-options')
const search_options = search_options_div.getElementsByClassName('search-option')
console.log(search_options)
let search_sites = undefined;
let search_confs = undefined;
let search_words = undefined;

// read JSON data
async function read_search_data() {
    const data = await fetch('/files/search_data.json')
    const json = await data.json()
    const search_sites = json['sites']
    const search_confs = json['score_confs']
    const search_words = json['words']
    return [search_sites, search_confs, search_words]
}
read_search_data().then(([sites, confs, words]) => {
    search_sites = sites;
    search_confs = confs;
    search_words = words;
    console.log(`Search data read successfully! Time Taken: ${performance.now() - start_time}ms`)
    console.log(`Sites: ${search_sites.length}`)
    console.log(`Confs: ${search_confs.length}`)
    console.log(`Words: ${Object.keys(search_words).length}`)
    console.log(search_words)
})

// show/hide elements when clicking elements/BG/div
function switch_search_visibility(e) {
    if(search_bg.classList.toggle('active')) {
        search_textbox.value = ''
        search_textbox.focus()
        onSearchChange()
    }
}
search_button.onclick = switch_search_visibility
search_bg.onclick = switch_search_visibility
// search_div.onclick = function(e) { // to not propagate the click to the BG when clicking the div
//     e.stopPropagation();
//     e.preventDefault();
// }

// update sites based on search string:
function onSearchChange(e) {
    if (typeof search_words === 'undefined') {
        console.log('Search words doesn\'t exist!')
        return
    }
    const text = search_textbox.value
    const ascii_text = text.normalize('NFKD').replace(/[\u0300-\u036f]/g, "") // remove diacritics
    const words = ascii_text.split(' ')
    let sites = []
    for(const word of words) {
        const word_conf = search_words[word]
        if (word_conf === undefined)
            continue
        const word_sites_idx = search_confs[word_conf]
        for (const word_site_idx of word_sites_idx) {
            if (sites.includes(word_site_idx))
                continue
            sites.push(word_site_idx)
            if (sites.length >= search_options.length)
                break
        }
    }

    console.log(sites)
    let index = 0;
    while(index < search_options.length) {
        let search_option = search_options[index]
        let search_option_title = search_option.getElementsByClassName('search-option-text')[0]
        let search_option_link = search_option.getElementsByClassName('search-option-link')[0]
        
        if (index < sites.length) {
            let site = search_sites[sites[index]]
            search_option.classList.remove('disabled')
            search_option.href = site['path']
            search_option_title.innerHTML = site['title']
            search_option_link.innerHTML = site['path']
            search_option.target = site['path'][0] == '/' ? '' : '_blank'
        }
        else {
            search_option.classList.add('disabled')
            search_option.href = '/'
            search_option_title.innerHTML = ''
            search_option_link.innerHTML = ''
            search_option.target = ""
        }
        index++
    }
}
search_textbox.oninput = onSearchChange