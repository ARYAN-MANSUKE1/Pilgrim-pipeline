<?php
/**
 * Plugin Name: Pilgrim - language ACF fields (REST)
 * Description: Registers the language Content/Title/Audio fields that the
 *   translation+audio pipeline reads and writes over the REST API. Mirrors the
 *   staging site. Own field group + own keys, so the existing "Temple Fields"
 *   group stays editable in the ACF UI and is never overridden.
 *   show_in_rest is REQUIRED: without it ACF silently drops these keys, writes
 *   return 200 OK but never persist, and reads never include the field.
 *   Idempotent - acf_add_local_field_group() is safe on every request.
 *   To remove: delete this file.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

add_action( 'acf/init', 'pilgrim_rest_language_fields' );
function pilgrim_rest_language_fields() {
    if ( ! function_exists( 'acf_add_local_field_group' ) ) { return; }
    $fields = array(
        array( 'key' => 'field_pilgrimrest_marathi_audio', 'name' => 'marathi_audio',
               'label' => 'Marathi Audio', 'type' => 'file', 'return_format' => 'array', ),
        array( 'key' => 'field_pilgrimrest_english_title', 'name' => 'english_title',
               'label' => 'English Title', 'type' => 'text',  ),
        array( 'key' => 'field_pilgrimrest_english_audio', 'name' => 'english_audio',
               'label' => 'English Audio', 'type' => 'file', 'return_format' => 'array', ),
        array( 'key' => 'field_pilgrimrest_hindi_audio', 'name' => 'hindi_audio',
               'label' => 'Hindi Audio', 'type' => 'file', 'return_format' => 'array', ),
        array( 'key' => 'field_pilgrimrest_gujarati_content', 'name' => 'gujarati_content',
               'label' => 'Gujarati Content', 'type' => 'wysiwyg', 'tabs' => 'all', 'toolbar' => 'full', 'media_upload' => 1, ),
        array( 'key' => 'field_pilgrimrest_gujarati_title', 'name' => 'gujarati_title',
               'label' => 'Gujarati Title', 'type' => 'text',  ),
        array( 'key' => 'field_pilgrimrest_gujarati_audio', 'name' => 'gujarati_audio',
               'label' => 'Gujarati Audio', 'type' => 'file', 'return_format' => 'array', ),
        array( 'key' => 'field_pilgrimrest_tamil_content', 'name' => 'tamil_content',
               'label' => 'Tamil Content', 'type' => 'wysiwyg', 'tabs' => 'all', 'toolbar' => 'full', 'media_upload' => 1, ),
        array( 'key' => 'field_pilgrimrest_tamil_title', 'name' => 'tamil_title',
               'label' => 'Tamil Title', 'type' => 'text',  ),
        array( 'key' => 'field_pilgrimrest_tamil_audio', 'name' => 'tamil_audio',
               'label' => 'Tamil Audio', 'type' => 'file', 'return_format' => 'array', ),
        array( 'key' => 'field_pilgrimrest_telugu_content', 'name' => 'telugu_content',
               'label' => 'Telugu Content', 'type' => 'wysiwyg', 'tabs' => 'all', 'toolbar' => 'full', 'media_upload' => 1, ),
        array( 'key' => 'field_pilgrimrest_telugu_title', 'name' => 'telugu_title',
               'label' => 'Telugu Title', 'type' => 'text',  ),
        array( 'key' => 'field_pilgrimrest_telugu_audio', 'name' => 'telugu_audio',
               'label' => 'Telugu Audio', 'type' => 'file', 'return_format' => 'array', ),
        array( 'key' => 'field_pilgrimrest_malayalam_content', 'name' => 'malayalam_content',
               'label' => 'Malayalam Content', 'type' => 'wysiwyg', 'tabs' => 'all', 'toolbar' => 'full', 'media_upload' => 1, ),
        array( 'key' => 'field_pilgrimrest_malayalam_title', 'name' => 'malayalam_title',
               'label' => 'Malayalam Title', 'type' => 'text',  ),
        array( 'key' => 'field_pilgrimrest_malayalam_audio', 'name' => 'malayalam_audio',
               'label' => 'Malayalam Audio', 'type' => 'file', 'return_format' => 'array', ),
        array( 'key' => 'field_pilgrimrest_kannada_content', 'name' => 'kannada_content',
               'label' => 'Kannada Content', 'type' => 'wysiwyg', 'tabs' => 'all', 'toolbar' => 'full', 'media_upload' => 1, ),
        array( 'key' => 'field_pilgrimrest_kannada_title', 'name' => 'kannada_title',
               'label' => 'Kannada Title', 'type' => 'text',  ),
        array( 'key' => 'field_pilgrimrest_kannada_audio', 'name' => 'kannada_audio',
               'label' => 'Kannada Audio', 'type' => 'file', 'return_format' => 'array', ),
        array( 'key' => 'field_pilgrimrest_bengali_content', 'name' => 'bengali_content',
               'label' => 'Bengali Content', 'type' => 'wysiwyg', 'tabs' => 'all', 'toolbar' => 'full', 'media_upload' => 1, ),
        array( 'key' => 'field_pilgrimrest_bengali_title', 'name' => 'bengali_title',
               'label' => 'Bengali Title', 'type' => 'text',  ),
        array( 'key' => 'field_pilgrimrest_bengali_audio', 'name' => 'bengali_audio',
               'label' => 'Bengali Audio', 'type' => 'file', 'return_format' => 'array', ),
        array( 'key' => 'field_pilgrimrest_punjabi_content', 'name' => 'punjabi_content',
               'label' => 'Punjabi Content', 'type' => 'wysiwyg', 'tabs' => 'all', 'toolbar' => 'full', 'media_upload' => 1, ),
        array( 'key' => 'field_pilgrimrest_punjabi_title', 'name' => 'punjabi_title',
               'label' => 'Punjabi Title', 'type' => 'text',  ),
        array( 'key' => 'field_pilgrimrest_punjabi_audio', 'name' => 'punjabi_audio',
               'label' => 'Punjabi Audio', 'type' => 'file', 'return_format' => 'array', ),
    );
    acf_add_local_field_group( array(
        'key' => 'group_pilgrim_rest_languages',
        'title' => 'Temple Fields (pipeline languages)',
        'fields' => $fields,
        'location' => array( array( array(
            'param' => 'post_type', 'operator' => '==', 'value' => 'temple',
        ) ) ),
        'show_in_rest' => 1,
    ) );
}
