<?php
/**
 * Single temple (CPT) — ACF multilingual content.
 *
 * @package Pilgrim_Data_Services
 */

get_header();

$thumbnail = get_the_post_thumbnail_url( get_the_ID(), 'full' );

// Ad slots. Each is rendered first and only placed on the page if it produced
// something, so a slot with no running ad takes no space at all -- with no ads
// the page is exactly the plain full-width layout.
$pds_ads = array();
foreach ( array( 'temple_top', 'temple_left', 'temple_right', 'temple_bottom' ) as $pds_slot ) {
	$pds_ads[ $pds_slot ] = '';
	if ( function_exists( 'pds_display_ad' ) ) {
		ob_start();
		pds_display_ad( $pds_slot );
		$pds_ads[ $pds_slot ] = trim( ob_get_clean() );
	}
}
$pds_cols_class = 'pds-temple-cols'
	. ( $pds_ads['temple_left'] ? ' has-left' : '' )
	. ( $pds_ads['temple_right'] ? ' has-right' : '' );
?>
<style>
.pds-ad-top-wrap { width:100%; margin-bottom:16px; text-align:center; }
.pds-ad-bottom-wrap { width:100%; margin-top:20px; text-align:center; }
.pds-temple-cols { display:grid; grid-template-columns:minmax(0,1fr); gap:20px; align-items:start; }
.pds-temple-cols.has-left { grid-template-columns:160px minmax(0,1fr); }
.pds-temple-cols.has-right { grid-template-columns:minmax(0,1fr) 160px; }
.pds-temple-cols.has-left.has-right { grid-template-columns:160px minmax(0,1fr) 160px; }
.pds-col-left, .pds-col-right { position:sticky; top:100px; }
@media (min-width:769px) and (max-width:1100px) {
	.pds-temple-cols { gap:12px; }
	.pds-temple-cols.has-left { grid-template-columns:120px minmax(0,1fr); }
	.pds-temple-cols.has-right { grid-template-columns:minmax(0,1fr) 120px; }
	.pds-temple-cols.has-left.has-right { grid-template-columns:120px minmax(0,1fr) 120px; }
}
@media (max-width:768px) {
	.pds-temple-cols { display:block; }
	.pds-col-left, .pds-col-right { display:none; }
	.pds-ad-top-wrap { margin-bottom:12px; }
}
</style>
<main id="content" class="site-main">
	<section class="temple-details" data-temple-id="<?php echo esc_attr( (string) get_the_ID() ); ?>" data-available-langs="<?php echo esc_attr( implode( ',', pds_get_temple_available_languages( get_the_ID() ) ) ); ?>">
		<div class="pds-container">
			<?php if ( $pds_ads['temple_top'] ) : ?>
				<div class="pds-ad-top-wrap"><?php echo $pds_ads['temple_top']; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- built by pds_display_ad() ?></div>
			<?php endif; ?>

			<div class="<?php echo esc_attr( $pds_cols_class ); ?>">
				<?php if ( $pds_ads['temple_left'] ) : ?>
					<div class="pds-col-left"><?php echo $pds_ads['temple_left']; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?></div>
				<?php endif; ?>

				<div class="pds-col-content">
					<div class="content-section">
						<?php if ( $thumbnail ) : ?>
							<div class="bg-feature-image" style="background-image: url('<?php echo esc_url( $thumbnail ); ?>');"></div>
						<?php endif; ?>

						<?php foreach ( pds_get_temple_languages() as $pds_lang_code => $pds_lang ) : ?>
							<div class="<?php echo esc_attr( $pds_lang_code ); ?>_lang dis_lang" style="display: <?php echo ( 'mr' === $pds_lang_code ) ? 'block' : 'none'; ?>;">
								<?php echo apply_filters( $pds_lang['field'], pds_get_field( $pds_lang['field'] ) ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
							</div>
						<?php endforeach; ?>
					</div>
					<?php if ( $pds_ads['temple_bottom'] ) : ?>
						<div class="pds-ad-bottom-wrap"><?php echo $pds_ads['temple_bottom']; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?></div>
					<?php endif; ?>
				</div>

				<?php if ( $pds_ads['temple_right'] ) : ?>
					<div class="pds-col-right"><?php echo $pds_ads['temple_right']; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?></div>
				<?php endif; ?>
			</div>
		</div>

		<div class="hero">
			<div class="pds-container">
				<div class="banner-slider" <?php echo $thumbnail ? 'style="background-image:url(' . esc_url( $thumbnail ) . ');background-size:cover;background-position:center;"' : ''; ?>>
					<?php
					$gall = pds_get_field( 'gallery', false, array() );
					if ( ! empty( $gall ) ) {
						echo do_shortcode( '[lightslider_looper]' );
					} elseif ( has_post_thumbnail() ) {
						echo '<div class="tl_slide_photo_container feature-img-only">';
						the_post_thumbnail( 'full' );
						echo '</div>';
					}
					?>
				</div>
			</div>
		</div>

		<div class="pds-container map-wrap">
			<div class="oper-street-map">
				<?php echo pds_get_field( 'google_map_ifream' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- iframe HTML from ACF ?>
			</div>
			<span class="backtohome">
				<a class="prev-icon" href="<?php echo esc_url( home_url( '/' ) ); ?>">
					<i class="fa fa-long-arrow-left" aria-hidden="true"></i>
					<?php esc_html_e( 'Back To Home', 'pilgrim-data-services' ); ?>
				</a>
			</span>
		</div>
	</section>

	<section class="related">
		<div class="pds-container">
			<?php
			while ( have_posts() ) :
				the_post();
				$related_posts = get_related_custom_posts_by_taxonomy( get_the_ID(), 'city' );
				if ( $related_posts && $related_posts->have_posts() ) :
					?>
					<div class="related-posts">
						<?php echo pds_lang_blocks( 'temples', 'div', '', 'block', 'h3' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- escaped inside ?>
						<ul class="related-post">
							<?php
							while ( $related_posts->have_posts() ) :
								$related_posts->the_post();
								?>
								<li class="related-items">
									<a href="<?php the_permalink(); ?>" <?php pds_the_temple_link_attrs(); ?>>
										<div class="post-feature-image" style="background-image: url('<?php echo esc_url( get_the_post_thumbnail_url() ); ?>');"></div>
										<?php foreach ( array_keys( pds_get_temple_languages() ) as $pds_code ) : ?>
											<div class="<?php echo esc_attr( $pds_code ); ?>_lang dis_lang" style="display: <?php echo 'mr' === $pds_code ? 'block' : 'none'; ?>;">
												<h5><?php echo esc_html( pds_get_temple_language_title( get_the_ID(), $pds_code ) ); ?></h5>
												<span class="view-details-btn"> <?php echo esc_html( pds_t( 'view_details', $pds_code ) ); ?> </span>
											</div>
										<?php endforeach; ?>
										<?php the_excerpt(); ?>
									</a>
								</li>
							<?php endwhile; ?>
						</ul>
					</div>
					<?php
					wp_reset_postdata();
				endif;
			endwhile;
			?>
		</div>
	</section>
</main>
<?php
get_footer();
