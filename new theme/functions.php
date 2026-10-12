<?php
/**
 * Pilgrim Data Services theme functions.
 *
 * @package Pilgrim_Data_Services
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'PDS_VERSION', '1.0.0' );
define( 'PDS_DIR', get_template_directory() );
define( 'PDS_URI', get_template_directory_uri() );

require_once PDS_DIR . '/inc/setup.php';
require_once PDS_DIR . '/inc/enqueue.php';
require_once PDS_DIR . '/inc/template-tags.php';
require_once PDS_DIR . '/inc/shortcodes.php';
require_once PDS_DIR . '/inc/ajax.php';
require_once PDS_DIR . '/inc/queries.php';
require_once PDS_DIR . '/inc/acf.php';
require_once PDS_DIR . '/inc/admin.php';

/**
 * Header language switcher: per-language audio button + keep the nav on one
 * line even when a language's labels (e.g. Malayalam) are much longer than
 * English.
 *
 * Live's Theme File Editor can only edit existing files, not create new
 * ones -- this lives here instead of its own inc/language-audio.php (which
 * is what staging uses) for that reason only; the code is identical.
 */

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

/*
 * ── Ads: region targeting, 4 slots (temple_top / temple_left / temple_right / temple_bottom) ──
 *
 * Staging keeps this in inc/ads.php; it lives here on live because the Theme
 * File Editor cannot create files. The Advertisements post type and its fields
 * are ACF/SCF settings (Custom Fields -> Tools -> Export/Import), not code.
 * single-temple.php only places a slot on the page when pds_display_ad()
 * printed something, so no running ad = no empty space.
 *
 * Differences from staging's inc/ads.php, both because 10Web caches whole pages:
 * - the phone/desktop creative is chosen by the browser (<picture>), not by
 *   sniffing the user agent on the server, which would cache one device's
 *   image for everyone;
 * - the click-tracking script is excluded from 10Web's script delay.
 * ponytail: impressions are counted per page render, so with the page cache
 * they undercount, and random rotation between several matching ads only
 * changes when the cache does. Real counts would need a JS beacon per view.
 *
 * Supports date formats: Y-m-d, d/m/Y, Ymd (20260926)
 * Supports old field names: campaign_status, placement, target_cities,
 *   ad_creative, start_date, end_date, destination_url, advertiser_name
 */
define( 'PDS_AD_POST_TYPE', 'advertisements' );

/* Read meta trying the new key, then the old key. */
function pds_ad_meta( $ad_id, $new_key, $old_key = '' ) {
	$v = get_post_meta( $ad_id, $new_key, true );
	if ( ( $v === '' || $v === false || $v === null ) && $old_key ) {
		$v = get_post_meta( $ad_id, $old_key, true );
		if ( ( $v === '' || $v === false ) && function_exists( 'get_field' ) ) {
			$v = get_field( $old_key, $ad_id );
		}
	}
	return $v;
}

/* Parse a date in any of the 3 stored formats. */
function pds_parse_ad_date( $raw ) {
	if ( empty( $raw ) ) return false;
	return DateTime::createFromFormat( 'Y-m-d', $raw )
		?: DateTime::createFromFormat( 'd/m/Y', $raw )
		?: DateTime::createFromFormat( 'Ymd',   $raw );
}

/* Image field (array / attachment ID / URL) to a URL. */
function pds_ad_image_url( $creative ) {
	if ( is_array( $creative ) && isset( $creative['url'] ) ) return esc_url( $creative['url'] );
	if ( is_numeric( $creative ) ) return (string) wp_get_attachment_image_url( (int) $creative, 'full' );
	return esc_url( (string) $creative );
}

/* Expand city term IDs to include all children. */
function pds_expand_city_terms( $term_ids ) {
	$out = (array) $term_ids;
	foreach ( $term_ids as $id ) {
		$kids = get_term_children( (int) $id, 'city' );
		if ( ! is_wp_error( $kids ) ) {
			$out = array_merge( $out, $kids );
		}
	}
	return array_unique( array_map( 'intval', $out ) );
}

/* Pick a running ad for this temple and slot (cached 20 min). */
function pds_get_matching_ad( $slot ) {
	if ( ! is_singular( 'temple' ) ) return false;

	$temple_id  = get_the_ID();
	$city_terms = wp_get_post_terms( $temple_id, 'city', array( 'fields' => 'ids' ) );
	if ( empty( $city_terms ) || is_wp_error( $city_terms ) ) return false;

	// The version is part of the key: bumping it (pds_flush_ad_cache) orphans every cached
	// pick at once, whether transients live in the options table or in an object cache.
	$cache_key = 'pds_ad_' . (int) get_option( 'pds_ad_cache_ver', 1 ) . '_' . $temple_id . '_' . sanitize_key( $slot );
	$ad_id     = get_transient( $cache_key );

	if ( false === $ad_id ) {
		$ads     = get_posts( array(
			'post_type'      => PDS_AD_POST_TYPE,
			'posts_per_page' => -1,
			'post_status'    => 'publish',
		) );
		$today   = new DateTime( 'today' );
		$matches = array();

		foreach ( $ads as $ad ) {
			$status = strtolower( (string) pds_ad_meta( $ad->ID, 'ad_status', 'campaign_status' ) );
			if ( $status !== 'active' ) continue;

			$db_slot = strtolower( str_replace( ' ', '_', (string) pds_ad_meta( $ad->ID, 'ad_placement', 'placement' ) ) );
			if ( $db_slot !== strtolower( str_replace( ' ', '_', $slot ) ) ) continue;

			$start_raw = pds_ad_meta( $ad->ID, 'ad_start_date', 'start_date' );
			$end_raw   = pds_ad_meta( $ad->ID, 'ad_end_date',   'end_date'   );
			if ( $start_raw && $end_raw ) {
				$s = pds_parse_ad_date( $start_raw );
				$e = pds_parse_ad_date( $end_raw );
				if ( $s && $e ) {
					$s->setTime( 0, 0, 0 );
					$e->setTime( 23, 59, 59 );
					if ( $today < $s || $today > $e ) continue;
				}
			}

			// The ad's target cities (parents include their districts) must overlap the temple's.
			$regions = pds_ad_meta( $ad->ID, 'ad_target_regions', 'target_cities' );
			if ( ! is_array( $regions ) ) {
				$maybe   = maybe_unserialize( $regions );
				$regions = is_array( $maybe ) ? $maybe : array_filter( explode( ',', (string) $regions ) );
			}
			$regions = array_filter( array_map( 'intval', $regions ) );
			if ( empty( $regions ) ) continue;
			if ( array_intersect( array_map( 'intval', $city_terms ), pds_expand_city_terms( $regions ) ) ) {
				$matches[] = $ad->ID;
			}
		}

		$ad_id = ! empty( $matches ) ? $matches[ array_rand( $matches ) ] : 0;
		set_transient( $cache_key, $ad_id, 20 * MINUTE_IN_SECONDS );
	}

	return $ad_id ? $ad_id : false;
}

/* Print an ad slot -- or nothing at all when no ad is running there. */
function pds_display_ad( $slot ) {
	$ad_id = pds_get_matching_ad( $slot );
	if ( ! $ad_id ) return;

	$desktop = pds_ad_image_url( pds_ad_meta( $ad_id, 'ad_creative_desktop', 'ad_creative' ) );
	$mobile  = pds_ad_image_url( get_post_meta( $ad_id, 'ad_creative_mobile', true ) );
	if ( ! $desktop ) $desktop = $mobile;
	if ( ! $desktop ) return;

	$link  = pds_ad_meta( $ad_id, 'ad_destination_url', 'destination_url' );
	$label = pds_ad_meta( $ad_id, 'ad_advertiser_name',  'advertiser_name' );

	update_post_meta( $ad_id, '_ad_impressions', (int) get_post_meta( $ad_id, '_ad_impressions', true ) + 1 );

	$img = '<picture>'
		. ( $mobile && $mobile !== $desktop ? '<source media="(max-width: 768px)" srcset="' . esc_url( $mobile ) . '">' : '' )
		. '<img src="' . esc_url( $desktop ) . '" alt="' . esc_attr( $label ?: 'Advertisement' ) . '" loading="lazy" />'
		. '</picture>';
	?>
	<div class="pds-ad-slot pds-ad-<?php echo sanitize_html_class( $slot ); ?>">
		<span class="pds-ad-label">Advertisement</span>
		<?php if ( $link ) : ?>
			<a href="<?php echo esc_url( $link ); ?>" target="_blank" rel="sponsored noopener"
			   onclick="if(window.pdsTrackClick)pdsTrackClick(<?php echo (int) $ad_id; ?>);"><?php echo $img; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- escaped above ?></a>
		<?php else : ?>
			<?php echo $img; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
		<?php endif; ?>
	</div>
	<?php
}

/* Click tracking. */
add_action( 'wp_ajax_pds_track_click',        'pds_ajax_track_click' );
add_action( 'wp_ajax_nopriv_pds_track_click', 'pds_ajax_track_click' );
function pds_ajax_track_click() {
	$ad_id = isset( $_POST['ad_id'] ) ? (int) $_POST['ad_id'] : 0;
	if ( $ad_id > 0 && PDS_AD_POST_TYPE === get_post_type( $ad_id ) ) {
		update_post_meta( $ad_id, '_ad_clicks', (int) get_post_meta( $ad_id, '_ad_clicks', true ) + 1 );
	}
	wp_die();
}

add_action( 'wp_footer', function () {
	if ( ! is_singular( 'temple' ) ) return;
	?>
	<script data-two-no-delay data-pagespeed-no-defer>
	function pdsTrackClick(adId){
		var d=new FormData();
		d.append('action','pds_track_click');
		d.append('ad_id',adId);
		navigator.sendBeacon
			? navigator.sendBeacon('<?php echo esc_url( admin_url( 'admin-ajax.php' ) ); ?>',d)
			: fetch('<?php echo esc_url( admin_url( 'admin-ajax.php' ) ); ?>',{method:'POST',body:d});
	}
	</script>
	<?php
}, 5 );

/* Cache flush: on every ad save, or visit any page with ?pds_flush_ads as an admin. */
function pds_flush_ad_cache() {
	global $wpdb;
	// Deleting rows alone does nothing on hosts with a persistent object cache (live
	// uses one): a paused or edited ad kept showing for up to 20 minutes.
	update_option( 'pds_ad_cache_ver', time(), false );
	return $wpdb->query( "DELETE FROM {$wpdb->options} WHERE option_name LIKE '_transient_pds_ad_%' OR option_name LIKE '_transient_timeout_pds_ad_%'" );
}
add_action( 'save_post_' . PDS_AD_POST_TYPE, function ( $id ) {
	if ( wp_is_post_autosave( $id ) || wp_is_post_revision( $id ) ) return;
	pds_flush_ad_cache();
} );
add_action( 'init', function () {
	if ( isset( $_GET['pds_flush_ads'] ) && current_user_can( 'manage_options' ) ) {
		$n = pds_flush_ad_cache();
		wp_die( 'Flushed ' . (int) $n . ' rows. <a href="' . esc_url( remove_query_arg( 'pds_flush_ads' ) ) . '">Back</a>' );
	}
} );

/*
 * Ad fields + counters for the Pilgrim Pipeline dashboard's Ads tab, readable and
 * writable over the REST API by logged-in editors only (context "edit"). Not SCF's
 * "Show in REST API" switch: /wp/v2/advertisements is public, and that switch would
 * publish every campaign's price and advertiser details to anyone.
 * Values are the same post meta SCF saves, so the wp-admin screen and the dashboard
 * edit the same data (dates as Ymd, cities as term-ID strings, image as attachment ID).
 */
add_action( 'init', function () {
	add_post_type_support( PDS_AD_POST_TYPE, 'custom-fields' );
	$fields = array(
		'advertiser_name' => 'string', 'ad_creative' => 'integer', 'destination_url' => 'string',
		'start_date' => 'string', 'end_date' => 'string', 'target_cities' => 'array',
		'placement' => 'string', 'campaign_status' => 'string', 'campaign_price' => 'number',
		'_ad_impressions' => 'integer', '_ad_clicks' => 'integer',
	);
	foreach ( $fields as $key => $type ) {
		$schema = array( 'type' => $type, 'context' => array( 'edit' ) );
		if ( 'array' === $type ) {
			$schema['items'] = array( 'type' => 'string' );
		}
		register_post_meta( PDS_AD_POST_TYPE, $key, array(
			'type'          => $type,
			'single'        => true,
			'show_in_rest'  => array( 'schema' => $schema ),
			'auth_callback' => function () { return current_user_can( 'edit_posts' ); },
		) );
	}
}, 20 );

/* Ad slot styles (the column layout itself is in single-temple.php). */
add_action( 'wp_head', function () {
	if ( ! is_singular( 'temple' ) ) return;
	?>
	<style id="pds-ad-styles">
	.pds-ad-slot { text-align: center; overflow: hidden; }
	.pds-ad-slot img { display: block; width: 100%; height: auto; border-radius: 6px; }
	/* width:100% alone scales an image to any height: a square picture put in the
	   top slot came out ~1140px tall and pushed the article off the screen. Capped,
	   and shrunk to fit (never stretched) when its shape doesn't suit the slot. */
	.pds-ad-temple_top img, .pds-ad-temple_bottom img { max-height: 250px; object-fit: contain; }
	.pds-ad-temple_left img, .pds-ad-temple_right img { max-height: 600px; object-fit: contain; }
	.pds-ad-label { display: block; font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: #aaa; margin-bottom: 4px; }
	</style>
	<?php
} );

/**
 * First-visit language-selection popup. Lets a new visitor pick a language
 * before browsing; remembered via a cookie so it only shows once. Dismissing
 * without choosing (X, or click outside) just keeps the site's default
 * language -- it never forces a choice.
 *
 * Both sites run the 10Web optimizer, which delays inline scripts until the
 * visitor's first interaction; see the note on the <script> tag below.
 */
function pds_language_selection_popup() {
	$languages = pds_get_temple_languages();
	?>
	<style>
	#pilgrim-lang-popup-overlay {
		position: fixed;
		inset: 0;
		background: rgba(30, 5, 5, 0.55);
		backdrop-filter: blur(3px);
		-webkit-backdrop-filter: blur(3px);
		z-index: 99999;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 16px;
		animation: pilgrim-fade-in 0.25s ease-out;
	}
	/* the display:flex above would otherwise override the hidden attribute, and the popup could never close */
	#pilgrim-lang-popup-overlay[hidden] { display: none; }
	@keyframes pilgrim-fade-in { from { opacity: 0; } to { opacity: 1; } }
	@keyframes pilgrim-pop-in { from { opacity: 0; transform: translateY(8px) scale(0.95); } to { opacity: 1; transform: translateY(0) scale(1); } }
	#pilgrim-lang-popup {
		background: #FEF6EC;
		border-radius: 18px;
		max-width: 325px;
		width: 100%;
		position: relative;
		box-shadow: 0 16px 46px rgba(0, 0, 0, 0.3);
		text-align: center;
		overflow: hidden;
		animation: pilgrim-pop-in 0.28s cubic-bezier(0.2, 0.8, 0.3, 1.1);
	}
	#pilgrim-lang-popup-head {
		background: linear-gradient(120deg, #9A031E 0%, #FB8B24 130%);
		padding: 18px 16px 14px;
		color: #ffffff;
	}
	#pilgrim-lang-popup-icon {
		width: 34px;
		height: 34px;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.18);
		display: inline-flex;
		align-items: center;
		justify-content: center;
		font-size: 17px;
		margin-bottom: 7px;
	}
	#pilgrim-lang-popup h2 {
		margin: 0 0 3px;
		font-size: 17px;
		font-weight: 700;
		color: #ffffff;
	}
	#pilgrim-lang-popup-sub {
		margin: 0;
		font-size: 12px;
		color: rgba(255, 255, 255, 0.9);
		line-height: 1.3;
	}
	#pilgrim-lang-popup-close {
		position: absolute;
		top: 9px;
		right: 9px;
		width: 25px;
		height: 25px;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.2);
		border: none;
		font-size: 15px;
		line-height: 1;
		cursor: pointer;
		color: #ffffff;
		transition: background 0.15s;
	}
	#pilgrim-lang-popup-close:hover { background: rgba(255, 255, 255, 0.35); }
	.pilgrim-lang-popup-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 8px;
		padding: 16px;
	}
	.pilgrim-lang-popup-btn {
		padding: 8px 5px;
		border: 1.5px solid #f0dcc4;
		border-radius: 10px;
		background: #ffffff;
		cursor: pointer;
		font-size: 14px;
		font-weight: 600;
		color: #620705;
		transition: border-color 0.15s, background 0.15s, transform 0.1s;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1px;
	}
	.pilgrim-lang-popup-btn span {
		font-size: 10px;
		font-weight: 400;
		color: #a08a78;
	}
	.pilgrim-lang-popup-btn:hover {
		border-color: #FB8B24;
		background: #FFDDBE;
		transform: translateY(-1px);
	}
	.pilgrim-lang-popup-btn:active { transform: translateY(0); }
	</style>

	<div id="pilgrim-lang-popup-overlay" hidden>
		<div id="pilgrim-lang-popup" role="dialog" aria-modal="true" aria-label="<?php esc_attr_e( 'Choose your language', 'pilgrim-data-services' ); ?>">
			<div id="pilgrim-lang-popup-head">
				<button type="button" id="pilgrim-lang-popup-close" aria-label="<?php esc_attr_e( 'Close', 'pilgrim-data-services' ); ?>">&times;</button>
				<div id="pilgrim-lang-popup-icon" aria-hidden="true">&#127760;</div>
				<h2><?php esc_html_e( 'Choose your language', 'pilgrim-data-services' ); ?></h2>
				<p id="pilgrim-lang-popup-sub"><?php esc_html_e( 'Browse temple pages in your preferred language', 'pilgrim-data-services' ); ?></p>
			</div>
			<div class="pilgrim-lang-popup-grid">
				<?php foreach ( $languages as $pds_popup_code => $pds_popup_lang ) : ?>
					<button type="button" class="pilgrim-lang-popup-btn" data-lang="<?php echo esc_attr( $pds_popup_code ); ?>">
						<?php echo esc_html( $pds_popup_lang['label'] ); ?>
						<span><?php echo esc_html( $pds_popup_lang['name'] ); ?></span>
					</button>
				<?php endforeach; ?>
			</div>
		</div>
	</div>

	<?php
	/*
	 * data-two-no-delay: the 10Web optimizer otherwise holds inline scripts back
	 * until the visitor interacts, so the popup could never be closed (what broke
	 * it on staging). The theme's own theme.js is still delayed, so this does not
	 * rely on it: it switches the page itself and writes theme.js's 'language'
	 * cookie, which theme.js reads on every page load. No DOMContentLoaded wait
	 * either -- this runs after the markup above, and a delayed run would miss it.
	 */
	?>
	<script data-two-no-delay data-pagespeed-no-defer>
	(function () {
		var overlay = document.getElementById('pilgrim-lang-popup-overlay');
		if (!overlay) return;

		function has(name) { return document.cookie.split('; ').some(function (c) { return c.indexOf(name + '=') === 0; }); }
		function setCookie(name, value) {
			document.cookie = name + '=' + value + '; max-age=' + 365 * 86400 + '; path=/; SameSite=Lax';
		}

		function show(code) {
			var sel = document.getElementById('language-select');
			if (sel) sel.value = code;
			document.querySelectorAll('.dis_lang').forEach(function (el) {
				el.style.display = el.classList.contains(code + '_lang') ? 'block' : 'none';
			});
		}

		function close(code) {
			overlay.hidden = true;
			setCookie('pilgrim_lang_seen', '1');  // closed without choosing: still never shown again
			if (!code) return;
			setCookie('language', code);            // theme.js restores the language from this on every page
			if (window.pdsLanguage) window.pdsLanguage.set(code);  // theme.js loaded: its switch (fires audio / nav updates)
			else show(code);
		}

		// theme.js applies the saved language only once the optimizer releases it (first scroll/touch);
		// until then every page would show Marathi. Apply it now.
		var saved = (document.cookie.match(/(?:^|; )language=([a-z]{2})(?:;|$)/) || [])[1];
		if (saved) show(saved);

		// Anyone who has picked a language (here or in the dropdown) or closed the popup never sees it again.
		else if (!has('pilgrim_lang_seen')) overlay.hidden = false;

		overlay.querySelectorAll('.pilgrim-lang-popup-btn').forEach(function (btn) {
			btn.addEventListener('click', function () { close(btn.getAttribute('data-lang')); });
		});
		document.getElementById('pilgrim-lang-popup-close').addEventListener('click', function () { close(); });
		overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });
		document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !overlay.hidden) close(); });
	})();
	</script>
	<?php
}
add_action( 'wp_footer', 'pds_language_selection_popup', 30 );
