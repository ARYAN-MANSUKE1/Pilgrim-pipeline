<?php
/**
 * ACF compatibility — field groups stay in the database / plugin.
 * This theme saves/loads ACF JSON from /acf-json so settings travel with the theme.
 *
 * Expected temple fields (from Hello Elementor child / SCF):
 * - marathi_title, hindi_title, gujrati_title
 * - mr_translation, en_translation, hi_translation
 * - gallery
 * - google_map_ifream
 *
 * @package Pilgrim_Data_Services
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Point ACF local JSON to this theme.
 *
 * @param string $path Path.
 * @return string
 */
function pds_acf_json_save_point( $path ) {
	return PDS_DIR . '/acf-json';
}
add_filter( 'acf/settings/save_json', 'pds_acf_json_save_point' );

/**
 * Load ACF JSON from this theme.
 *
 * @param array $paths Paths.
 * @return array
 */
function pds_acf_json_load_point( $paths ) {
	$paths[] = PDS_DIR . '/acf-json';
	return $paths;
}
add_filter( 'acf/settings/load_json', 'pds_acf_json_load_point' );

/**
 * Admin notice if ACF Pro is missing (theme depends on get_field).
 */
function pds_acf_missing_notice() {
	if ( function_exists( 'get_field' ) ) {
		return;
	}
	if ( ! current_user_can( 'activate_plugins' ) ) {
		return;
	}
	echo '<div class="notice notice-warning"><p>';
	echo esc_html__( 'Pilgrim Data Services theme expects Secure Custom Fields (or Advanced Custom Fields) to be active for temple fields and Gutenberg ACF blocks.', 'pilgrim-data-services' );
	echo '</p></div>';
}
add_action( 'admin_notices', 'pds_acf_missing_notice' );

/**
 * Ensure temple CPT / taxonomies exist if not already registered by ACF/plugin.
 * Does not override existing registrations.
 */
function pds_maybe_register_temple_cpt() {
	if ( ! post_type_exists( 'temple' ) ) {
		register_post_type(
			'temple',
			array(
				'labels'       => array(
					'name'          => __( 'Temples', 'pilgrim-data-services' ),
					'singular_name' => __( 'Temple', 'pilgrim-data-services' ),
				),
				'public'       => true,
				'has_archive'  => true,
				'rewrite'      => array( 'slug' => 'temple' ),
				'show_in_rest' => true,
				'menu_icon'    => 'dashicons-building',
				'supports'     => array( 'title', 'editor', 'thumbnail', 'excerpt', 'custom-fields' ),
			)
		);
	}

	if ( ! taxonomy_exists( 'city' ) ) {
		register_taxonomy(
			'city',
			array( 'temple' ),
			array(
				'labels'            => array(
					'name'          => __( 'Cities', 'pilgrim-data-services' ),
					'singular_name' => __( 'City', 'pilgrim-data-services' ),
				),
				'hierarchical'      => true,
				'public'            => true,
				'show_in_rest'      => true,
				'rewrite'           => array( 'slug' => 'city' ),
			)
		);
	}

	if ( ! taxonomy_exists( 'temple-category' ) ) {
		register_taxonomy(
			'temple-category',
			array( 'temple' ),
			array(
				'labels'            => array(
					'name'          => __( 'Temple Categories', 'pilgrim-data-services' ),
					'singular_name' => __( 'Temple Category', 'pilgrim-data-services' ),
				),
				'hierarchical'      => true,
				'public'            => true,
				'show_in_rest'      => true,
				'rewrite'           => array( 'slug' => 'temple-category' ),
			)
		);
	}
}
add_action( 'init', 'pds_maybe_register_temple_cpt', 5 );

/**
 * Register the 7 pipeline languages ACF never had a field group for
 * (Gujarati, Tamil, Telugu, Malayalam, Kannada, Bengali, Punjabi).
 *
 * The data was already being written to these exact postmeta keys by
 * app/tasks/wp_client.py (CONTENT_FIELD_KEYS / TITLE_FIELD_KEYS) and
 * get_field() was already reading it via ACF's raw-meta fallback for an
 * unregistered field -- that's why the front end works. This just makes
 * WordPress admin (and the REST "acf" object) aware these fields exist, so
 * they show up as editable boxes on the temple edit screen instead of being
 * invisible there. show_in_rest exposes them over the API the same way
 * marathi_title etc. already are.
 */
add_action( 'acf/init', 'pds_register_missing_language_fields' );
function pds_register_missing_language_fields() {
	if ( ! function_exists( 'acf_add_local_field_group' ) ) {
		return;
	}

	$languages = array(
		'gujarati'  => 'Gujarati',
		'tamil'     => 'Tamil',
		'telugu'    => 'Telugu',
		'malayalam' => 'Malayalam',
		'kannada'   => 'Kannada',
		'bengali'   => 'Bengali',
		'punjabi'   => 'Punjabi',
	);

	$fields = array();
	foreach ( $languages as $slug => $label ) {
		$fields[] = array(
			'key'          => 'field_pds_' . $slug . '_title',
			'name'         => $slug . '_title',
			'label'        => $label . ' Title',
			'type'         => 'text',
		);
		$fields[] = array(
			'key'          => 'field_pds_' . $slug . '_content',
			'name'         => $slug . '_content',
			'label'        => $label . ' Content',
			'type'         => 'wysiwyg',
			'tabs'         => 'all',
			'toolbar'      => 'full',
			'media_upload' => 1,
		);
		$fields[] = array(
			'key'           => 'field_pds_' . $slug . '_audio',
			'name'          => $slug . '_audio',
			'label'         => $label . ' Audio',
			'type'          => 'file',
			'return_format' => 'array',
		);
	}

	// english_title and the audio fields for Marathi/English/Hindi were never
	// registered anywhere on live -- unlike the other core-language fields
	// (marathi_title, hindi_title, mr/en/hi_translation), which some earlier,
	// now-gone setup already registered. Confirmed via a direct REST check:
	// migrate_to_live.py's preflight refused to run because these 4 specific
	// keys were absent from live's "acf" REST object (WordPress silently
	// drops unregistered ACF keys on write, so this must exist before the
	// migration can copy real audio/title data into them). Staging already
	// has all 4, so this only needs adding here.
	$fields[] = array(
		'key'   => 'field_pds_english_title',
		'name'  => 'english_title',
		'label' => 'English Title',
		'type'  => 'text',
	);
	foreach ( array( 'marathi', 'english', 'hindi' ) as $slug ) {
		$fields[] = array(
			'key'           => 'field_pds_' . $slug . '_audio_core',
			'name'          => $slug . '_audio',
			'label'         => ucfirst( $slug ) . ' Audio',
			'type'          => 'file',
			'return_format' => 'array',
		);
	}

	acf_add_local_field_group(
		array(
			'key'          => 'group_pds_extra_languages',
			'title'        => 'Temple Fields (additional pipeline languages)',
			'fields'       => $fields,
			'location'     => array(
				array(
					array(
						'param'    => 'post_type',
						'operator' => '==',
						'value'    => 'temple',
					),
				),
			),
			'show_in_rest' => 1,
		)
	);
}
