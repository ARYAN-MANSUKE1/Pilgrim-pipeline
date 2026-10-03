<?php
/**
 * Header language switcher: per-language audio button + keep the nav on one
 * line even when a language's labels (e.g. Malayalam) are much longer than
 * English.
 *
 * @package Pilgrim_Data_Services
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Read a language's audio field into a plain URL, whatever shape ACF hands
 * back (array from a real 'file' field, a numeric attachment ID, or a raw
 * URL string for a field that was never registered).
 *
 * @param string $field ACF field name.
 * @return string
 */
function pds_audio_url( $field ) {
	$value = pds_get_field( $field );
	if ( empty( $value ) ) {
		return '';
	}
	if ( is_array( $value ) ) {
		return isset( $value['url'] ) ? esc_url( $value['url'] ) : '';
	}
	if ( is_numeric( $value ) ) {
		$url = wp_get_attachment_url( (int) $value );
		return $url ? esc_url( $url ) : '';
	}
	return esc_url( (string) $value );
}

/**
 * Output the audio button/player and the nav-fit script in the footer.
 * ponytail: font/padding shrink is a linear search (<=60 steps), not a
 * closed-form fit -- fine at header-nav scale, would need a smarter
 * algorithm if this ever ran on a much larger element.
 */
function pds_language_audio_and_nav_fit() {
	$audio = array();
	if ( is_singular( 'temple' ) ) {
		foreach ( pds_get_temple_languages() as $code => $lang ) {
			$audio[ $code ] = empty( $lang['audio'] ) ? '' : pds_audio_url( $lang['audio'] );
		}
	}
	$audio_json = wp_json_encode( $audio );
	$is_temple  = is_singular( 'temple' ) ? 'true' : 'false';
	?>
	<style>
	#pilgrim-audio-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 30px;
		height: 30px;
		border-radius: 50%;
		border: 2px solid rgba(255,255,255,0.55);
		background: transparent;
		color: #ffffff;
		font-size: 14px;
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
	</style>

	<audio id="pilgrim-global-audio" preload="none" style="display:none;">
		<source id="pilgrim-audio-src" src="" type="audio/mpeg">
	</audio>

	<script>
	(function () {
		var AUDIO     = <?php echo $audio_json; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>;
		var IS_TEMPLE = <?php echo $is_temple; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>;
		// Captured once from whatever gap the CSS naturally gives before any
		// override runs, then re-applied identically for every language.
		// Hardcoding a pixel number here was guesswork that kept not
		// matching the theme's own default spacing -- this measures the
		// real thing instead, so English and Malayalam get the exact same
		// gap by construction, not by trial and error.
		var capturedLogoGap = null;

		function injectAudioBtn() {
			var sel = document.getElementById('language-select');
			if (!sel || document.getElementById('pilgrim-audio-btn')) return;
			var btn = document.createElement('button');
			btn.id = 'pilgrim-audio-btn';
			btn.type = 'button';
			btn.setAttribute('aria-label', 'Play audio');
			btn.innerHTML = '&#128266;';
			if (!IS_TEMPLE) btn.classList.add('hidden');
			btn.addEventListener('click', function (e) {
				e.stopPropagation();
				toggleAudio(sel.value);
			});
			sel.insertAdjacentElement('afterend', btn);

			// The select and button are siblings inside the same wrapper div,
			// but that div is itself a flex child of the header row -- when
			// the row is tight, the browser wraps the select and button onto
			// separate lines instead of moving the whole wrapper as one
			// unit. Forcing the wrapper into its own nowrap flex row keeps
			// them glued together no matter what the row around them does.
			var wrap = sel.parentElement;
			if (wrap) {
				wrap.style.display = 'inline-flex';
				wrap.style.alignItems = 'center';
				wrap.style.flexWrap = 'nowrap';
				wrap.style.whiteSpace = 'nowrap';
			}
		}

		function setPlayState(playing) {
			var btn = document.getElementById('pilgrim-audio-btn');
			if (!btn) return;
			btn.classList.toggle('playing', playing);
			btn.innerHTML = playing ? '&#9646;&#9646;' : '&#128266;';
		}

		function updateAudioForLang(lang) {
			var audioEl = document.getElementById('pilgrim-global-audio');
			var srcEl   = document.getElementById('pilgrim-audio-src');
			var url     = AUDIO[lang] || '';
			if (audioEl && !audioEl.paused) { audioEl.pause(); setPlayState(false); }
			if (srcEl) { srcEl.src = url; }
			if (audioEl) { audioEl.load(); }
			var btn = document.getElementById('pilgrim-audio-btn');
			if (btn) { btn.style.visibility = url ? 'visible' : 'hidden'; }
		}

		function toggleAudio(lang) {
			var url     = AUDIO[lang] || '';
			var audioEl = document.getElementById('pilgrim-global-audio');
			var srcEl   = document.getElementById('pilgrim-audio-src');
			if (!url || !audioEl || !srcEl) return;
			if (srcEl.src !== url) { srcEl.src = url; audioEl.load(); }
			if (audioEl.paused) {
				audioEl.play().then(function () { setPlayState(true); }).catch(function () { setPlayState(false); });
			} else {
				audioEl.pause();
				setPlayState(false);
			}
		}

		// Shrink the nav's font-size and link padding just enough to stay on
		// one line, no matter how long a language's labels run (Malayalam
		// wraps "Contact Us" onto a second line at the same font size
		// English fits on one line at). Checking whether the container
		// dropped below the logo isn't enough -- the <li>s can wrap onto a
		// second line while the container itself stays put, which is
		// exactly this failure mode. Instead compare the first and last
		// menu item's own vertical position: if they differ, the menu has
		// wrapped, regardless of what the container did. Resets first each
		// run so a shorter language grows back to full size.
		function fitNavToOneLine() {
			var nav = document.getElementById('menu-primary-menu');
			if (!nav) return;

			var items = nav.querySelectorAll('li');
			var links = nav.querySelectorAll('li > a');
			if (items.length < 2) return;

			// The logo and nav are flex siblings in the same row. Pushing the
			// nav right with margin only works if the logo can't be squeezed
			// to make room for it -- without this, the browser shrank the
			// LOGO instead of respecting the nav's margin, since nothing told
			// it the logo was off-limits. Lock it once, permanently.
			var branding = document.querySelector('.site-branding');
			if ( branding ) {
				branding.style.flexShrink = '0';
			}

			// Reset to bare CSS (no inline override) before measuring, so the
			// very first measurement reflects the theme's real default gap,
			// not a value we imposed ourselves on a previous run.
			nav.style.fontSize = '';
			nav.style.marginLeft = '';
			links.forEach(function (a) {
				a.style.paddingLeft = '';
				a.style.paddingRight = '';
				a.style.whiteSpace = 'nowrap';
			});

			if ( capturedLogoGap === null && branding ) {
				var bRect = branding.getBoundingClientRect();
				var nRect = nav.getBoundingClientRect();
				capturedLogoGap = Math.max( 0, nRect.left - bRect.right );
			}
			// Shrinking font/padding closes the gap between nav items, but
			// never guaranteed any gap between the logo and the FIRST item --
			// at tight widths (long Malayalam labels eating most of the row)
			// "Home" ends up touching "Services". Re-impose the SAME gap the
			// browser gave for free at the default (short) language.
			if ( capturedLogoGap !== null ) {
				nav.style.marginLeft = capturedLogoGap + 'px';
			}

			function isWrapped() {
				var firstTop = items[0].getBoundingClientRect().top;
				var lastTop  = items[items.length - 1].getBoundingClientRect().top;
				return (lastTop - firstTop) > 4;
			}

			var size    = parseFloat(getComputedStyle(nav).fontSize);
			var minSize = 10;
			var pad     = links.length ? (parseFloat(getComputedStyle(links[0]).paddingLeft) || 0) : 0;
			var minPad  = 4;
			var attempts = 0;
			while (isWrapped() && (size > minSize || pad > minPad) && attempts < 60) {
				if (size > minSize) { size -= 0.5; nav.style.fontSize = size + 'px'; }
				if (pad > minPad) {
					pad -= 1;
					links.forEach(function (a) { a.style.paddingLeft = pad + 'px'; a.style.paddingRight = pad + 'px'; });
				}
				attempts++;
			}

			// A size that JUST barely stops wrapping still looks cramped --
			// the fit is right at the edge, so a single re-render (a font
			// hinting shift, a scrollbar appearing) can wrap it again. Shrink
			// one extra step past the bare minimum for breathing room.
			if (size > minSize) { size -= 1; nav.style.fontSize = size + 'px'; }
		}

		document.addEventListener('DOMContentLoaded', function () {
			injectAudioBtn();
			var sel = document.getElementById('language-select');

			if (sel) {
				updateAudioForLang(sel.value);
				sel.addEventListener('change', function () {
					updateAudioForLang(sel.value);
					fitNavToOneLine();
				});
			}
			fitNavToOneLine();
		});
		window.addEventListener('load', fitNavToOneLine);
	})();
	</script>
	<?php
}
add_action( 'wp_footer', 'pds_language_audio_and_nav_fit', 20 );
