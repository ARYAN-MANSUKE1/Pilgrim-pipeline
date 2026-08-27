<?php
/**
 * Plugin Name: Pilgrim - language switcher + audio (frontend)
 * Description: Front-end half of the multilingual temple pages: the language
 *   pills, the per-language audio player, and the translated site chrome.
 *   Code is lifted verbatim from the staging theme's functions.php so live and
 *   staging behave identically. Shipped as a plugin so live's own functions.php
 *   is never touched -- it contains admin features (the City taxonomy filter)
 *   that staging does not have.
 *   Companion to "Pilgrim - language ACF fields (REST)", which registers the
 *   fields this reads. To remove: deactivate and delete.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

function pilgrim_default_languages() {
    // code => [English name, native self-name shown in the dropdown]
    $known = array(
        'mr' => array( 'Marathi', 'मराठी' ),   'en' => array( 'English', 'English' ),
        'hi' => array( 'Hindi', 'हिन्दी' ),     'gj' => array( 'Gujarati', 'ગુજરાતી' ),
        'ta' => array( 'Tamil', 'தமிழ்' ),      'te' => array( 'Telugu', 'తెలుగు' ),
        'ml' => array( 'Malayalam', 'മലയാളം' ), 'kn' => array( 'Kannada', 'ಕನ್ನಡ' ),
        'bn' => array( 'Bengali', 'বাংলা' ),    'pa' => array( 'Punjabi', 'ਪੰਜਾਬੀ' ),
    );
    $out = array();
    foreach ( $known as $code => $pair ) {
        $out[ $code ] = array(
            'name' => $pair[0], 'native' => $pair[1],
            'fields' => false, 'chrome' => true, 'visible' => true,
        );
    }
    return $out;
}

function pilgrim_get_languages() {
    $langs = get_option( 'pilgrim_languages', null );
    if ( ! is_array( $langs ) || empty( $langs ) ) {
        $langs = pilgrim_default_languages();
        update_option( 'pilgrim_languages', $langs, false );
    }
    return $langs;
}

function pilgrim_audio_url( $field ) {
    $v = get_field( $field );
    if ( empty( $v ) ) {
        return '';
    }
    if ( is_array( $v ) ) {
        return esc_url( isset( $v['url'] ) ? $v['url'] : '' );
    }
    if ( is_numeric( $v ) ) {
        return esc_url( (string) wp_get_attachment_url( (int) $v ) );
    }
    return esc_url( (string) $v );
}

function pilgrim_extend_language_and_audio() {

    $audio_mr = '';
    $audio_en = '';
    $audio_hi = '';
    $audio_gj = '';
    $audio_ta = '';
    $audio_te = '';
    $audio_ml = '';
    $audio_kn = '';
    $audio_bn = '';
    $audio_pa = '';

    if ( is_singular('temple') ) {
        $audio_mr = pilgrim_audio_url('marathi_audio');
        $audio_en = pilgrim_audio_url('english_audio');
        $audio_hi = pilgrim_audio_url('hindi_audio');
        $audio_gj = pilgrim_audio_url('gujarati_audio');
        $audio_ta = pilgrim_audio_url('tamil_audio');
        $audio_te = pilgrim_audio_url('telugu_audio');
        $audio_ml = pilgrim_audio_url('malayalam_audio');
        $audio_kn = pilgrim_audio_url('kannada_audio');
        $audio_bn = pilgrim_audio_url('bengali_audio');
        $audio_pa = pilgrim_audio_url('punjabi_audio');
    }

    $audio_json = json_encode( array(
        'mr' => $audio_mr,
        'en' => $audio_en,
        'hi' => $audio_hi,
        'gj' => $audio_gj,
        'ta' => $audio_ta,
        'te' => $audio_te,
        'ml' => $audio_ml,
        'kn' => $audio_kn,
        'bn' => $audio_bn,
        'pa' => $audio_pa,
    ));
    $is_temple = is_singular('temple') ? 'true' : 'false';

    // Cached chrome-string dictionary (survives independently of Elementor/migrations).
    $ui_i18n = get_option( 'pilgrim_ui_i18n', array() );
    if ( ! is_array( $ui_i18n ) ) {
        $ui_i18n = array();
    }
    $ui_i18n_json = wp_json_encode( $ui_i18n );

    // Language registry -- drives which dropdown options appear (visible=true only).
    $langs_json = wp_json_encode( pilgrim_get_languages() );
    ?>

    <style>
    #pilgrim-audio-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 34px;
        height: 34px;
        border-radius: 50%;
        border: 2px solid rgba(255,255,255,0.55);
        background: transparent;
        color: #ffffff;
        font-size: 15px;
        cursor: pointer;
        margin-left: 6px;
        vertical-align: middle;
        transition: background 0.18s, border-color 0.18s;
        padding: 0;
        line-height: 1;
        flex-shrink: 0;
    }
    #pilgrim-audio-btn:hover { background: rgba(255,255,255,0.18); border-color: #ffffff; }
    #pilgrim-audio-btn.playing { background: #FB8B24; border-color: #FB8B24; }
    #pilgrim-audio-btn.hidden { display: none !important; }
    #lang-audio-wrap { display: inline-flex; align-items: center; gap: 6px; }
    </style>

    <audio id="pilgrim-global-audio" preload="none" style="display:none;">
        <source id="pilgrim-audio-src" src="" type="audio/mpeg">
    </audio>

    <script>
    (function () {
        var AUDIO     = <?php echo $audio_json; ?>;
        var IS_TEMPLE = <?php echo $is_temple; ?>;
        var UI_I18N   = <?php echo $ui_i18n_json; ?>;   // { lang: { key: text } }, from wp_options
        var LANGS     = <?php echo $langs_json; ?>;     // { code: {name, native, fields, chrome, visible} }

        // Hardcoded English fallback: guarantees no chrome string is ever blank,
        // even before a language is translated or if the option is empty.
        var UI_FALLBACK_EN = {
            nav_home:"Home", nav_about:"About Us", nav_temples:"Temples",
            nav_state:"State", nav_sponsors:"Sponsors", nav_contact:"Contact Us",
            nav_privacy:"Privacy Policy", nav_terms:"Terms & Conditions",
            s_instagram:"Instagram", s_facebook:"Facebook", s_youtube:"YouTube",
            copyright:"All Rights Reserved."
        };

        function applyUiI18n(lang) {
            var dict = UI_I18N[lang] || {};
            var en   = UI_I18N['en'] || {};
            document.querySelectorAll('[data-i18n]').forEach(function (el) {
                var key = el.getAttribute('data-i18n');
                var text = dict[key] || en[key] || UI_FALLBACK_EN[key];
                if (text) el.textContent = text;
            });
        }

        // Keep the nav menu on ONE line, beside the logo, no matter how long a
        // language's labels run -- and no matter what language gets added
        // later.
        //
        // Verified against the theme's actual header markup: the flex row
        // that wraps is  .site-branding (logo)  vs  .main-header-extra-class
        // (which contains the nav, the language dropdown, AND the mobile
        // hamburger toggle) -- both siblings under .header-inner. The nav
        // itself is nested INSIDE .main-header-extra-class, not a sibling of
        // the logo, so comparing the nav's own position to its previous
        // sibling (an earlier attempt) never worked -- there wasn't one.
        //
        // Fix: detect wrap by comparing .main-header-extra-class's top to
        // .site-branding's bottom. If it's no longer on the same row, shrink
        // both the nav's font-size AND each link's horizontal padding (there's
        // more competing for space in that row than just the nav -- the
        // language dropdown and hamburger toggle too, so font alone may not
        // be enough). Resets both to default first each run so English (or
        // any short language) grows back to full size.
        function fitNavToOneLine() {
            var nav = document.getElementById('menu-english-primary-menu');
            var branding = document.querySelector('.site-branding');
            var extra = document.querySelector('.main-header-extra-class');
            if (!nav || !branding || !extra) return;

            var links = nav.querySelectorAll('li > a');
            nav.style.fontSize = '';
            links.forEach(function (a) { a.style.paddingLeft = ''; a.style.paddingRight = ''; });

            function isWrapped() {
                return extra.getBoundingClientRect().top > branding.getBoundingClientRect().bottom - 4;
            }

            var size = parseFloat(getComputedStyle(nav).fontSize);
            var minSize = 10;   // px floor -- never shrink past readable
            var pad = links.length ? (parseFloat(getComputedStyle(links[0]).paddingLeft) || 0) : 0;
            var minPad = 4;
            var attempts = 0;
            while (isWrapped() && (size > minSize || pad > minPad) && attempts < 60) {
                if (size > minSize) { size -= 0.5; nav.style.fontSize = size + 'px'; }
                if (pad > minPad) {
                    pad -= 1;
                    links.forEach(function (a) { a.style.paddingLeft = pad + 'px'; a.style.paddingRight = pad + 'px'; });
                }
                attempts++;
            }
        }

        document.addEventListener('DOMContentLoaded', function () {

            var sel = document.getElementById('language-select');

            // Add every visible language (from the registry) not already an option.
            // Adding/removing a language from the dropdown is now just flipping its
            // "visible" flag via the dashboard -- no code change, ever.
            if (sel) {
                var vals = Array.from(sel.options).map(function(o){ return o.value; });
                Object.keys(LANGS).forEach(function (code) {
                    var lang = LANGS[code];
                    if (!lang.visible || vals.indexOf(code) !== -1) return;
                    var opt = document.createElement('option');
                    opt.value = code;
                    opt.textContent = lang.native || lang.name;
                    sel.appendChild(opt);
                });
            }

            // On a temple page, drop any language that has no translated content
            // on THIS temple. Without this every temple offers all ten languages
            // and most of them open a blank panel -- live has 2,282 temples and
            // only a fraction are translated at any given moment. Purely a
            // display filter: nothing is deleted, and a language reappears by
            // itself the moment its content is filled in.
            if (sel && IS_TEMPLE) {
                var empties = [], kept = 0;
                Array.prototype.slice.call(sel.options).forEach(function (opt) {
                    var block = document.querySelector('.' + opt.value + '_lang');
                    if (block && block.textContent.trim()) { kept++; }
                    else { empties.push(opt); }
                });
                // Never strip the selector bare -- if we somehow matched nothing,
                // leave it exactly as the theme rendered it.
                if (kept > 0) {
                    empties.forEach(function (o) {
                        if (o.parentNode) { o.parentNode.removeChild(o); }
                    });
                }
            }

            // Inject audio button next to select
            injectAudioBtn();

            // Restore saved language from cookie
            var savedLang = getCookie('language');
            if (savedLang && ['mr','en','hi','gj','ta','te','ml','kn','bn','pa'].indexOf(savedLang) !== -1) {
                if (sel) sel.value = savedLang;
                updateAudioForLang(savedLang);
                applyUiI18n(savedLang);
                syncPillButtons((savedLang === 'gj') ? 'gu' : savedLang);
            } else {
                applyUiI18n('mr');   // page default before any selection
            }
            fitNavToOneLine();

            // Hook into existing select change — add audio update on top
            if (sel) {
                sel.addEventListener('change', function () {
                    updateAudioForLang(sel.value);
                    applyUiI18n(sel.value);
                    fitNavToOneLine();
                });
            }

            // Wire in-page .lang-btn pills (single-temple.php)
            document.querySelectorAll('.lang-btn').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    var lang = btn.dataset.lang;
                    var mappedLang = (lang === 'gu') ? 'gj' : lang;
                    if (sel) {
                        sel.value = mappedLang;
                        if (typeof toggleLanguage === 'function') toggleLanguage(mappedLang);
                    }
                    updateAudioForLang(mappedLang);
                    applyUiI18n(mappedLang);
                    fitNavToOneLine();
                    syncPillButtons(lang);
                });
            });
        });

        // Re-check after full page load too (fonts can shift text width after
        // the DOMContentLoaded measurement above).
        window.addEventListener('load', fitNavToOneLine);

        function injectAudioBtn() {
            var sel = document.getElementById('language-select');
            if (!sel || document.getElementById('pilgrim-audio-btn')) return;
            var wrap = document.createElement('span');
            wrap.id = 'lang-audio-wrap';
            sel.parentNode.insertBefore(wrap, sel);
            wrap.appendChild(sel);
            var btn = document.createElement('button');
            btn.id = 'pilgrim-audio-btn';
            btn.setAttribute('aria-label', 'Play audio');
            btn.setAttribute('type', 'button');
            btn.innerHTML = '&#128266;';
            if (!IS_TEMPLE) btn.classList.add('hidden');
            btn.addEventListener('click', function (e) { e.stopPropagation(); toggleAudio(); });
            wrap.appendChild(btn);
        }

        function syncPillButtons(lang) {
            document.querySelectorAll('.lang-btn').forEach(function (btn) {
                var isActive = btn.dataset.lang === lang;
                btn.classList.toggle('active', isActive);
                btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
            });
        }

        function updateAudioForLang(lang) {
            var url      = AUDIO[lang] || '';
            var audioEl = document.getElementById('temple-audio-player');
            var playerEl = document.getElementById('temple-audio-player');
            var srcEl2   = document.getElementById('temple-audio-source');
            var audioMsg = document.getElementById('audio-unavailable');

       if (playerEl && !playerEl.paused) {
    playerEl.pause();
    setPlayState(false);
}

            if (playerEl && srcEl2) {
                if (url) {
                    srcEl2.src = url;
                    playerEl.load();
                    playerEl.style.display = 'block';
                    if (audioMsg) audioMsg.style.display = 'none';
                } else {
                    playerEl.pause();
                    playerEl.style.display = 'none';
                    if (audioMsg) audioMsg.style.display = 'block';
                }
            }
        }

        function toggleAudio() {
            var sel     = document.getElementById('language-select');
            var lang    = sel ? sel.value : 'mr';
            var url     = AUDIO[lang] || '';
            var audioEl = document.getElementById('pilgrim-global-audio');
            var srcEl   = document.getElementById('pilgrim-audio-src');

            if (!url) {
                var btn = document.getElementById('pilgrim-audio-btn');
                if (btn) { btn.innerHTML = '&#128263;'; setTimeout(function(){ btn.innerHTML = '&#128266;'; }, 1200); }
                return;
            }
            if (srcEl && srcEl.src !== url) { srcEl.src = url; audioEl.load(); }
            if (audioEl.paused) {
                audioEl.play().then(function(){ setPlayState(true); }).catch(function(){ setPlayState(false); });
            } else {
                audioEl.pause(); setPlayState(false);
            }
        }

        function setPlayState(playing) {
            var btn = document.getElementById('pilgrim-audio-btn');
            if (!btn) return;
            btn.classList.toggle('playing', playing);
            btn.innerHTML = playing ? '&#9646;&#9646;' : '&#128266;';
            btn.setAttribute('aria-label', playing ? 'Pause audio' : 'Play audio');
        }

        document.addEventListener('DOMContentLoaded', function () {
            var audioEl = document.getElementById('pilgrim-global-audio');
            if (audioEl) audioEl.addEventListener('ended', function(){ setPlayState(false); });
        });

        function getCookie(name) {
            var nameEQ = name + '=';
            var ca = document.cookie.split(';');
            for (var i = 0; i < ca.length; i++) {
                var c = ca[i].trim();
                if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length);
            }
            return null;
        }
    })();
    </script>

    <?php
}

// Override marquee slider with 4-language version
remove_shortcode('temple_slider');
add_shortcode('temple_slider', 'temple_marquee_slider_shortcode_v2');

add_action( 'wp_footer', 'pilgrim_extend_language_and_audio', 20 );
