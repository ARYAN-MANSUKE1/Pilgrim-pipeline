<?php
/**
 * Template tags / helpers.
 *
 * @package Pilgrim_Data_Services
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * URL for a media filename, even if it was re-uploaded to a new month folder.
 *
 * Prefers an attachment whose file still exists on disk (newest first),
 * then a theme asset under assets/images/, then the newest attachment URL.
 *
 * @param string $filename       Attachment basename, e.g. Banner-Design-023.jpg.
 * @param string $theme_relative Optional path under assets/images/.
 * @return string
 */
function pds_image_url( $filename, $theme_relative = '' ) {
	static $cache = array();

	$filename       = ltrim( (string) $filename, '/' );
	$theme_relative = $theme_relative ? ltrim( (string) $theme_relative, '/' ) : $filename;
	$key            = $filename . '|' . $theme_relative;

	if ( isset( $cache[ $key ] ) ) {
		return $cache[ $key ];
	}

	$theme_path = get_template_directory() . '/assets/images/' . $theme_relative;
	$theme_url  = get_template_directory_uri() . '/assets/images/' . $theme_relative;

	global $wpdb;
	$ids = $wpdb->get_col(
		$wpdb->prepare(
			"SELECT post_id FROM {$wpdb->postmeta}
			WHERE meta_key = '_wp_attached_file'
			AND ( meta_value = %s OR meta_value LIKE %s )
			ORDER BY post_id DESC",
			$filename,
			'%/' . $wpdb->esc_like( $filename )
		)
	);

	foreach ( (array) $ids as $attachment_id ) {
		$path = get_attached_file( (int) $attachment_id );
		if ( $path && file_exists( $path ) ) {
			$url = wp_get_attachment_url( (int) $attachment_id );
			if ( $url ) {
				$cache[ $key ] = $url;
				return $url;
			}
		}
	}

	if ( file_exists( $theme_path ) ) {
		$cache[ $key ] = $theme_url;
		return $theme_url;
	}

	if ( ! empty( $ids ) ) {
		$url = wp_get_attachment_url( (int) $ids[0] );
		if ( $url ) {
			$cache[ $key ] = $url;
			return $url;
		}
	}

	$cache[ $key ] = $theme_url;
	return $theme_url;
}

/**
 * Attributes that stop 10Web / LiteSpeed / WP Rocket from replacing img src
 * with an empty SVG placeholder.
 *
 * @return string
 */
function pds_skip_lazy_attr() {
	return 'data-no-lazy="1" data-skip-lazy="1"';
}

/**
 * Safe ACF field getter with fallback.
 *
 * @param string $key     Field name.
 * @param mixed  $post_id Post ID or false for current.
 * @param mixed  $default Default value.
 * @return mixed
 */
function pds_get_field( $key, $post_id = false, $default = '' ) {
	if ( function_exists( 'get_field' ) ) {
		$value = get_field( $key, $post_id );
		return ( null === $value || false === $value || '' === $value ) ? $default : $value;
	}
	return $default;
}

/**
 * Supported temple body-copy languages (SCF / ACF field map).
 *
 * Titles stay on the existing fields; body copy uses `*_translation`.
 * Gujarati is included only when a body-copy field is present on a temple.
 *
 * @return array<string, array<string, string>>
 */
function pds_get_temple_languages() {
	$languages = array(
		'mr' => array(
			'label' => 'मराठी',
			'name'  => __( 'Marathi', 'pilgrim-data-services' ),
			'field' => 'mr_translation',
			'title' => 'marathi_title',
			'audio' => 'marathi_audio',
		),
		'en' => array(
			'label' => 'English',
			'name'  => __( 'English', 'pilgrim-data-services' ),
			'field' => 'en_translation',
			'title' => 'english_title',
			'audio' => 'english_audio',
		),
		'hi' => array(
			'label' => 'हिन्दी',
			'name'  => __( 'Hindi', 'pilgrim-data-services' ),
			'field' => 'hi_translation',
			'title' => 'hindi_title',
			'audio' => 'hindi_audio',
		),
		// ponytail: field names below match app/tasks/wp_client.py's
		// CONTENT_FIELD_KEYS / TITLE_FIELD_KEYS exactly -- the pipeline writes
		// to these, not to a "{code}_translation" pattern. Gujarati was
		// previously pointed at gj_translation / gujrati_title (typo'd,
		// neither field the pipeline ever wrote to), so it silently showed
		// nothing despite data existing under gujarati_content.
		'gj' => array(
			'label' => 'ગુજરાતી',
			'name'  => __( 'Gujarati', 'pilgrim-data-services' ),
			'field' => 'gujarati_content',
			'title' => 'gujarati_title',
			'audio' => 'gujarati_audio',
		),
		'ta' => array(
			'label' => 'தமிழ்',
			'name'  => __( 'Tamil', 'pilgrim-data-services' ),
			'field' => 'tamil_content',
			'title' => 'tamil_title',
			'audio' => 'tamil_audio',
		),
		'te' => array(
			'label' => 'తెలుగు',
			'name'  => __( 'Telugu', 'pilgrim-data-services' ),
			'field' => 'telugu_content',
			'title' => 'telugu_title',
			'audio' => 'telugu_audio',
		),
		'ml' => array(
			'label' => 'മലയാളം',
			'name'  => __( 'Malayalam', 'pilgrim-data-services' ),
			'field' => 'malayalam_content',
			'title' => 'malayalam_title',
			'audio' => 'malayalam_audio',
		),
		'kn' => array(
			'label' => 'ಕನ್ನಡ',
			'name'  => __( 'Kannada', 'pilgrim-data-services' ),
			'field' => 'kannada_content',
			'title' => 'kannada_title',
			'audio' => 'kannada_audio',
		),
		'bn' => array(
			'label' => 'বাংলা',
			'name'  => __( 'Bengali', 'pilgrim-data-services' ),
			'field' => 'bengali_content',
			'title' => 'bengali_title',
			'audio' => 'bengali_audio',
		),
		'pa' => array(
			'label' => 'ਪੰਜਾਬੀ',
			'name'  => __( 'Punjabi', 'pilgrim-data-services' ),
			'field' => 'punjabi_content',
			'title' => 'punjabi_title',
			'audio' => 'punjabi_audio',
		),
	);

	/**
	 * Filter the temple language map.
	 *
	 * @param array $languages Language definitions keyed by code.
	 */
	return apply_filters( 'pds_temple_languages', $languages );
}

/**
 * Current front-end language from the existing cookie (default Marathi).
 *
 * @return string
 */
function pds_get_current_language() {
	$languages = pds_get_temple_languages();
	$lang      = isset( $_COOKIE['language'] ) ? sanitize_key( wp_unslash( $_COOKIE['language'] ) ) : 'mr';

	if ( ! isset( $languages[ $lang ] ) ) {
		return 'mr';
	}

	return $lang;
}

/**
 * Word count of body copy, excluding heading tags.
 *
 * @param mixed $html Raw or formatted field value.
 * @return int
 */
function pds_temple_body_word_count( $html ) {
	if ( ! is_string( $html ) || '' === trim( $html ) ) {
		return 0;
	}

	$without_headings = preg_replace( '/<h[1-6][^>]*>.*?<\/h[1-6]>/is', ' ', $html );
	$without_headings = preg_replace( '/<(script|style)[^>]*>.*?<\/\1>/is', ' ', (string) $without_headings );
	$text             = wp_strip_all_tags( (string) $without_headings, true );
	$text             = html_entity_decode( $text, ENT_QUOTES, 'UTF-8' );
	$text             = str_replace( array( "\xc2\xa0", '&nbsp;' ), ' ', $text );
	$text             = preg_replace( '/\s+/u', ' ', trim( $text ) );

	if ( ! is_string( $text ) || '' === $text ) {
		return 0;
	}

	$words = preg_split( '/\s+/u', $text, -1, PREG_SPLIT_NO_EMPTY );
	return is_array( $words ) ? count( $words ) : 0;
}

/**
 * Whether temple HTML includes media (counts as body data).
 *
 * @param mixed $html Raw or formatted field value.
 * @return bool
 */
function pds_temple_content_has_media( $html ) {
	return is_string( $html ) && (bool) preg_match( '/<(img|iframe|video|audio|figure)\b/i', $html );
}

/**
 * Whether temple copy is missing or too thin to display.
 *
 * Insufficient when empty, under 5 body words, or heading tags with no body data.
 *
 * @param mixed $html Raw or formatted field value.
 * @return bool
 */
function pds_temple_content_is_empty( $html ) {
	if ( ! is_string( $html ) || '' === trim( $html ) ) {
		return true;
	}

	if ( pds_temple_content_has_media( $html ) ) {
		return false;
	}

	return pds_temple_body_word_count( $html ) < 5;
}

/**
 * Language codes that have body copy for a temple.
 *
 * Uses raw post meta so listing pages do not pay ACF/SCF formatting cost.
 *
 * @param int $post_id Temple ID.
 * @return string[]
 */
function pds_get_temple_available_languages( $post_id ) {
	static $cache = array();

	$post_id = absint( $post_id );
	if ( ! $post_id ) {
		return array();
	}

	if ( isset( $cache[ $post_id ] ) ) {
		return $cache[ $post_id ];
	}

	$available = array();
	foreach ( pds_get_temple_languages() as $code => $config ) {
		if ( empty( $config['field'] ) ) {
			continue;
		}

		$raw = get_post_meta( $post_id, $config['field'], true );
		if ( ! pds_temple_content_is_empty( $raw ) ) {
			$available[] = $code;
		}
	}

	$cache[ $post_id ] = $available;
	return $available;
}

/**
 * Temple title for a language, falling back to the post title.
 *
 * @param int    $post_id Temple ID.
 * @param string $lang    Language code.
 * @return string
 */
function pds_get_temple_language_title( $post_id, $lang ) {
	$post_id    = absint( $post_id );
	$languages  = pds_get_temple_languages();
	$post_title = $post_id ? get_the_title( $post_id ) : '';

	if ( ! isset( $languages[ $lang ] ) ) {
		return $post_title;
	}

	$title_field = $languages[ $lang ]['title'];
	if ( $title_field ) {
		$title = pds_get_field( $title_field, $post_id, '' );
		if ( is_string( $title ) && '' !== trim( $title ) ) {
			return $title;
		}
	}

	return $post_title;
}

/**
 * Formatted temple body copy for one language.
 *
 * @param int    $post_id Temple ID.
 * @param string $lang    Language code.
 * @return string
 */
function pds_get_temple_language_content( $post_id, $lang ) {
	$post_id   = absint( $post_id );
	$languages = pds_get_temple_languages();

	if ( ! $post_id || ! isset( $languages[ $lang ] ) ) {
		return '';
	}

	$field   = $languages[ $lang ]['field'];
	$content = pds_get_field( $field, $post_id, '' );
	if ( pds_temple_content_is_empty( $content ) ) {
		return '';
	}

	$content = apply_filters( $field, $content );
	return wp_kses_post( $content );
}

/**
 * Unavailable-language message for the fallback popup.
 *
 * @param string $lang Language code the visitor asked for.
 * @return string
 */
function pds_get_temple_unavailable_message( $lang ) {
	$messages = array(
		'en' => __( 'This temple information is not available in English.', 'pilgrim-data-services' ),
		'mr' => 'ही मंदिर माहिती मराठीत उपलब्ध नाही.',
		'hi' => 'यह मंदिर जानकारी हिन्दी में उपलब्ध नहीं है।',
		'gj' => 'આ મંદિરની માહિતી ગુજરાતીમાં ઉપલબ્ધ નથી.',
	);

	if ( isset( $messages[ $lang ] ) ) {
		return $messages[ $lang ];
	}
	if ( function_exists( 'pds_t' ) && 'en' !== $lang ) {
		$translated = pds_t( 'unavailable', $lang );
		if ( '' !== $translated && $translated !== pds_t( 'unavailable', 'en' ) ) {
			return $translated;
		}
	}

	$languages = pds_get_temple_languages();
	$name      = isset( $languages[ $lang ]['name'] ) ? $languages[ $lang ]['name'] : $lang;

	return sprintf(
		/* translators: %s: language name */
		__( 'This temple information is not available in %s.', 'pilgrim-data-services' ),
		$name
	);
}

/**
 * Public language list (code + label) for JS / buttons.
 *
 * @param string[] $codes Optional subset of language codes.
 * @return array<int, array<string, string>>
 */
function pds_format_temple_language_buttons( $codes = array() ) {
	$languages = pds_get_temple_languages();
	$codes     = ! empty( $codes ) ? $codes : array_keys( $languages );
	$buttons   = array();

	foreach ( $codes as $code ) {
		if ( ! isset( $languages[ $code ] ) ) {
			continue;
		}

		$buttons[] = array(
			'code'  => $code,
			'label' => $languages[ $code ]['label'],
		);
	}

	return $buttons;
}

/**
 * HTML attributes for temple card links (popup intercept).
 *
 * @param int $post_id Temple ID.
 * @return string
 */
function pds_get_temple_link_attrs( $post_id = 0 ) {
	$post_id = absint( $post_id ? $post_id : get_the_ID() );
	if ( ! $post_id ) {
		return '';
	}

	$langs = pds_get_temple_available_languages( $post_id );

	return sprintf(
		'class="pds-temple-link" data-temple-id="%d" data-available-langs="%s"',
		$post_id,
		esc_attr( implode( ',', $langs ) )
	);
}

/**
 * Echo temple card link attributes.
 *
 * @param int $post_id Temple ID.
 */
function pds_the_temple_link_attrs( $post_id = 0 ) {
	echo pds_get_temple_link_attrs( $post_id ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- escaped in getter.
}

/**
 * Markup for the temple popup body (content or fallback).
 *
 * @param int    $post_id Temple ID.
 * @param string $lang    Requested language.
 * @return array<string, mixed>
 */
function pds_get_temple_popup_payload( $post_id, $lang ) {
	$post_id   = absint( $post_id );
	$languages = pds_get_temple_languages();
	$lang      = sanitize_key( $lang );

	if ( ! isset( $languages[ $lang ] ) ) {
		$lang = pds_get_current_language();
	}

	$available = pds_get_temple_available_languages( $post_id );
	$has       = in_array( $lang, $available, true );
	$permalink = get_permalink( $post_id );

	ob_start();
	?>
	<div class="pds-temple-popup__panel pds-temple-popup__panel--fallback" data-lang="<?php echo esc_attr( $lang ); ?>">
		<p class="pds-temple-popup__message"><?php echo esc_html( pds_get_temple_unavailable_message( $lang ) ); ?></p>
		<?php if ( ! empty( $available ) ) : ?>
			<div class="pds-temple-popup__langs" role="group" aria-label="<?php esc_attr_e( 'Available languages', 'pilgrim-data-services' ); ?>">
				<?php foreach ( pds_format_temple_language_buttons( $available ) as $button ) : ?>
					<a
						class="pds-temple-popup__lang-btn"
						href="<?php echo esc_url( $permalink ); ?>"
						data-lang="<?php echo esc_attr( $button['code'] ); ?>"
					>
						<?php echo esc_html( $button['label'] ); ?>
					</a>
				<?php endforeach; ?>
			</div>
		<?php endif; ?>
	</div>
	<?php

	return array(
		'has_content' => $has,
		'lang'        => $lang,
		'available'   => pds_format_temple_language_buttons( $available ),
		'permalink'   => $permalink,
		'html'        => ob_get_clean(),
	);
}

/**
 * Related temples by taxonomy.
 *
 * @param int    $post_id         Post ID.
 * @param string $taxonomy        Taxonomy slug.
 * @param int    $number_of_posts Count.
 * @return WP_Query|false
 */
function get_related_custom_posts_by_taxonomy( $post_id, $taxonomy, $number_of_posts = 3 ) {
	$terms = wp_get_post_terms( $post_id, $taxonomy );
	if ( empty( $terms ) || is_wp_error( $terms ) ) {
		return false;
	}

	$term_ids = wp_list_pluck( $terms, 'term_id' );

	$args = array(
		'post_type'           => get_post_type( $post_id ),
		'post__not_in'        => array( $post_id ),
		'posts_per_page'      => $number_of_posts,
		'tax_query'           => array(
			array(
				'taxonomy' => $taxonomy,
				'field'    => 'term_id',
				'terms'    => $term_ids,
			),
		),
		'ignore_sticky_posts' => 1,
	);

	return new WP_Query( $args );
}

/**
 * Render primary nav HTML.
 *
 * @return string
 */
function pds_get_primary_menu() {
	$locations = array( 'primary', 'menu-1' );
	foreach ( $locations as $location ) {
		if ( has_nav_menu( $location ) ) {
			return wp_nav_menu(
				array(
					'theme_location' => $location,
					'container'      => false,
					'menu_class'     => 'menu',
					'menu_id'        => 'menu-primary-menu',
					'fallback_cb'    => false,
					'echo'           => false,
				)
			);
		}
	}
	return '';
}

/**
 * Render footer nav HTML.
 *
 * @return string
 */
function pds_get_footer_menu() {
	$locations = array( 'footer', 'menu-2' );
	foreach ( $locations as $location ) {
		if ( has_nav_menu( $location ) ) {
			return wp_nav_menu(
				array(
					'theme_location' => $location,
					'container'      => false,
					'menu_class'     => 'menu',
					'fallback_cb'    => false,
					'echo'           => false,
				)
			);
		}
	}
	return '';
}

/**
 * Theme copyright text (Customizer).
 *
 * @return string
 */
function pds_get_copyright() {
	$default = sprintf(
		/* translators: %s: year */
		__( '© %s Pilgrim Data Services | All Rights Reserved.', 'pilgrim-data-services' ),
		gmdate( 'Y' )
	);
	return get_theme_mod( 'pds_copyright_text', $default );
}

/**
 * Register Customizer settings carried from Hello Elementor footer copyright.
 */
function pds_customize_register( $wp_customize ) {
	$wp_customize->add_section(
		'pds_footer',
		array(
			'title'    => __( 'Footer', 'pilgrim-data-services' ),
			'priority' => 120,
		)
	);

	$wp_customize->add_setting(
		'pds_copyright_text',
		array(
			'default'           => '',
			'sanitize_callback' => 'wp_kses_post',
		)
	);

	$wp_customize->add_control(
		'pds_copyright_text',
		array(
			'label'       => __( 'Copyright text', 'pilgrim-data-services' ),
			'description' => __( 'Supports HTML. Leave empty for default.', 'pilgrim-data-services' ),
			'section'     => 'pds_footer',
			'type'        => 'textarea',
		)
	);
}
add_action( 'customize_register', 'pds_customize_register' );
