"""
Image generation command for ei CLI.

Provides text-to-image generation using DALL-E and GPT Image models.
"""

import webbrowser
from typing import Any

import click
from click.exceptions import Exit
from rich.console import Console
from rich.panel import Panel

from ei_cli.cli.utils import require_api_key
from ei_cli.core.errors import MissingAPIKeyError
from ei_cli.services.ai_service import ImageGenerationResult, ImageVariationsResult
from ei_cli.services.base import ServiceError
from ei_cli.services.factory import ServiceFactory


def _handle_tool_unavailable(
    console: Console,
    error: str | None,
) -> None:
    """Handle when image tool is unavailable."""
    console.print(
        f"[red]✗[/red] Image generation tool not available: {error}",
    )
    console.print(
        "\n[yellow]Tip:[/yellow] Set your OpenAI API key:",
    )
    console.print("  export EI_API_KEY=your-key-here")
    raise Exit(1)


def _display_analytics_summary(console: Console, ai_service) -> None:
    """Display analytics summary for Phase 3 feature."""
    try:
        summary = ai_service.get_analytics_summary()
        
        if summary["total_requests"] > 0:
            console.print("\n📊 [bold cyan]Analytics Summary[/bold cyan]")
            console.print(f"Total Requests: {summary['total_requests']}")
            console.print(f"Success Rate: {summary['success_rate']:.1%}")
            avg_complexity = summary["average_complexity"]
            console.print(f"Average Complexity: {avg_complexity:.2f}")
            
            if summary["categories"]:
                console.print("Categories Generated:")
                for category, count in summary["categories"].items():
                    console.print(f"  • {category}: {count}")
        else:
            console.print("\n📊 No analytics data available yet")
    except Exception:
        # Fail silently for analytics - don't break the main flow
        pass


def _display_variations_result(
    console: Console,
    result: ImageVariationsResult,
    size: str,
    quality: str,
    open_browser: bool,
) -> None:
    """Display image variations result."""
    console.print()

    # Build display text
    display_parts = [
        f"[bold cyan]{result.total_generated} Variations Generated![/bold cyan]\n",
        f"[green]Strategy:[/green] {result.metadata['strategy']}",
        f"[dim]Base Prompt:[/dim] {result.base_prompt}",
        f"[dim]Model:[/dim] {result.variations[0].model if result.variations else 'gpt-image-1'}",
        f"[dim]Size:[/dim] {size}",
        f"[dim]Quality:[/dim] {quality}",
    ]

    console.print(Panel(
        "\n".join(display_parts),
        title="✨ Image Variations Result",
        border_style="green",
    ))

    # Show individual variation details
    console.print(f"\n[bold]Generated {result.total_generated} variations:[/bold]")
    for i, variation in enumerate(result.variations, 1):
        if variation.local_path:
            console.print(f"  {i}. [green]Saved to:[/green] {variation.local_path}")
        else:
            console.print(f"  {i}. [green]Generated[/green] (base64 data)")

    # Show revised prompts if available
    enhanced_prompts = [v.revised_prompt for v in result.variations if v.revised_prompt]
    if enhanced_prompts:
        console.print()
        console.print(Panel(
            "\n".join(f"{i+1}. {prompt}" for i, prompt in enumerate(enhanced_prompts)),
            title="[bold yellow]Enhanced Prompts[/bold yellow]",
            border_style="yellow",
        ))

    # Handle browser opening for first variation
    if open_browser and result.variations:
        first_variation = result.variations[0]
        if first_variation.image_url.startswith("http"):  # pragma: no cover
            console.print()
            console.print("[cyan]Opening first variation in browser...[/cyan]")
            webbrowser.open(first_variation.image_url)
        elif first_variation.local_path:
            console.print()
            console.print(f"[cyan]First variation saved to: {first_variation.local_path}[/cyan]")


def _process_batch_file(
    batch_file: str,
    console: Console,
    ai_service: Any,
    size: str,
    quality: str,
    output_path: str | None,
    output_json: bool,
    no_enhance: bool,
    variations: int | None,
    variation_strategy: str,
    no_cache: bool,
) -> None:
    """Process multiple prompts from a batch file."""
    from pathlib import Path
    
    batch_path = Path(batch_file)
    
    try:
        with batch_path.open("r", encoding="utf-8") as f:
            prompts = [line.strip() for line in f if line.strip()]
        
        if not prompts:
            console.print("[yellow]No prompts found in batch file[/yellow]")
            return None
        
        num_prompts = len(prompts)
        console.print(f"[cyan]Processing {num_prompts} prompts from batch[/cyan]")
        
        # Create output directory if provided
        batch_output_dir = None
        if output_path:
            batch_output_dir = Path(output_path)
            batch_output_dir.mkdir(parents=True, exist_ok=True)
        
        successful = 0
        failed = 0
        
        for i, prompt in enumerate(prompts, 1):
            prompt_preview = prompt[:50] + ("..." if len(prompt) > 50 else "")
            console.print(f"\n[bold]Processing {i}/{num_prompts}:[/bold]")
            console.print(f"[dim]{prompt_preview}[/dim]")
            
            try:
                # Set output path for this batch item
                current_output = None
                if batch_output_dir:
                    safe_name = "".join(
                        c if c.isalnum() or c in (" ", "-", "_") else "_"
                        for c in prompt
                    )[:30].strip()
                    filename = f"batch_{i:03d}_{safe_name}.png"
                    current_output = batch_output_dir / filename
                
                # Generate image or variations
                if variations:
                    result = ai_service.generate_image_variations(
                        prompt=prompt,
                        count=variations,
                        size=size,
                        quality=quality,
                        output_dir=current_output.parent if current_output else None,
                        show_progress=False,
                        enhance_prompt=not no_enhance,
                        variation_strategy=variation_strategy,
                        use_cache=not no_cache,
                    )
                    if output_json:
                        _display_variations_json_output(
                            console, result, size, quality,
                        )
                    else:
                        count = result.total_generated
                        console.print(f"[green]✓ Generated {count} variations[/green]")
                else:
                    result = ai_service.generate_image(
                        prompt=prompt,
                        size=size,
                        quality=quality,
                        output_path=current_output,
                        show_progress=False,
                        enhance_prompt=not no_enhance,
                        use_cache=not no_cache,
                    )
                    if output_json:
                        _display_json_output(console, result, size, quality)
                    else:
                        path = result.local_path or "memory"
                        console.print(f"[green]✓ Generated and saved to: {path}[/green]")
                
                successful += 1
                
            except Exception as e:
                console.print(f"[red]✗ Failed: {e}[/red]")
                failed += 1
        
        # Show summary
        console.print(f"\n[bold cyan]Batch Processing Complete![/bold cyan]")
        console.print(f"Successful: [green]{successful}[/green]")
        console.print(f"Failed: [red]{failed}[/red]")
        console.print(f"Total: {successful + failed}")
        
    except Exception as e:
        console.print(f"[red]Error processing batch file: {e}[/red]")
        
    return None


def _apply_preset(
    preset: str, current_size: str, current_quality: str,
) -> tuple[str, str]:
    """Apply advanced parameter preset combinations (Phase 4 feature)."""
    presets = {
        "portrait": ("1024x1536", "high"),     # Tall format, high detail
        "landscape": ("1536x1024", "high"),    # Wide format, high detail
        "square": ("1024x1024", "medium"),     # Square format, balanced
        "hd": ("1792x1024", "high"),          # Ultra-wide, maximum detail
        "artistic": ("1024x1024", "high"),     # Square, artistic quality
    }
    
    if preset in presets:
        preset_size, preset_quality = presets[preset]
        # Only override if current values are defaults
        size = preset_size if current_size == "auto" else current_size
        quality = (
            preset_quality if current_quality == "auto" else current_quality
        )
        return size, quality
    
    return current_size, current_quality


def _display_variations_json_output(
    console: Console,
    variations_result: ImageVariationsResult,
    size: str,
    quality: str,
) -> None:
    """Display variations result as JSON."""
    output = {
        "base_prompt": variations_result.base_prompt,
        "strategy": variations_result.metadata["strategy"],
        "total_generated": variations_result.total_generated,
        "size": size,
        "quality": quality,
        "variations": [
            {
                "url": variation.image_url,
                "revised_prompt": variation.revised_prompt,
                "model": variation.model,
                "local_path": (
                    str(variation.local_path) if variation.local_path else None
                ),
            }
            for variation in variations_result.variations
        ],
        "metadata": variations_result.metadata,
    }
    console.print_json(data=output)


def _display_result(
    console: Console,
    result: ImageGenerationResult,
    size: str,
    quality: str,
    open_browser: bool,
) -> None:
    """Display image generation result."""
    console.print()

    # Build display text
    display_parts = [
        "[bold cyan]Image Generated Successfully![/bold cyan]\n",
    ]

    # Show local path if saved, otherwise show data URL info
    if result.local_path:
        display_parts.append(
            f"[green]Saved to:[/green] {result.local_path}",
        )
    else:
        # For data URLs, show that image was generated successfully
        display_parts.append("[green]Image:[/green] Generated (base64 data)")

    display_parts.extend([
        f"[dim]Model:[/dim] {result.model}",
        f"[dim]Size:[/dim] {size}",
        f"[dim]Quality:[/dim] {quality}",
    ])

    console.print(Panel(
        "\n".join(display_parts),
        title="✨ Image Generation Result",
        border_style="green",
    ))

    if result.revised_prompt:  # pragma: no cover
        console.print()
        console.print(Panel(
            result.revised_prompt,
            title="[bold yellow]Revised Prompt[/bold yellow]",
            border_style="yellow",
        ))

    # Open browser for http URLs (though gpt-image-1 returns base64)
    if (open_browser and
            result.image_url.startswith("http")):  # pragma: no cover
        console.print()
        console.print("[cyan]Opening image in browser...[/cyan]")
        webbrowser.open(result.image_url)
    elif open_browser and result.local_path:
        # For local files, show path (opening files needs more security checks)
        console.print()
        console.print(f"[cyan]Image saved to: {result.local_path}[/cyan]")
        console.print(
            "[dim]Use --open with saved images in your file manager[/dim]",
        )


def _display_json_output(
    console: Console,
    result: ImageGenerationResult,
    size: str,
    quality: str,
) -> None:
    """Display result as JSON."""
    output = {
        "url": result.image_url,
        "revised_prompt": result.revised_prompt,
        "model": result.model,
        "size": size,
        "quality": quality,
        "local_path": str(result.local_path) if result.local_path else None,
    }
    console.print_json(data=output)


@click.command()
@click.argument("prompt", required=False)
@click.option(
    "--size",
    "-s",
    default="1024x1024",
    type=click.Choice([
        "1024x1024",
        "1536x1024",
        "1024x1536",
        "auto",
    ]),
    help="Image size - 1024x1024 (square), 1536x1024 (landscape), "
         "1024x1536 (portrait), or auto (default: 1024x1024)",
)
@click.option(
    "--quality",
    "-q",
    default="auto",
    type=click.Choice(["low", "medium", "high", "auto"]),
    help="Quality level - low/medium/high/auto. "
         "auto lets gpt-image-1 select optimal quality (default: auto)",
)
@click.option(
    "--open",
    "open_browser",
    is_flag=True,
    help="Open the generated image in browser",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(),
    help="Path to save generated image (file or directory)",
)
@click.option(
    "--no-enhance",
    is_flag=True,
    help="Disable intelligent prompt enhancement (default: enabled)",
)
@click.option(
    "--show-analytics",
    is_flag=True,
    help="Show analytics summary after generation (Phase 3 feature)",
)
@click.option(
    "--variations",
    "-v",
    type=click.IntRange(1, 6),
    help="Generate multiple variations (1-6, Phase 4 feature)",
)
@click.option(
    "--variation-strategy",
    type=click.Choice(["creative", "technical", "style", "mixed"]),
    default="creative",
    help="Variation strategy: creative (diverse interpretations), "
         "technical (parameter variations), style (artistic styles), "
         "mixed (combination) - default: creative",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable intelligent caching (Phase 4 feature)",
)
@click.option(
    "--cache-stats",
    is_flag=True,
    help="Show cache statistics (Phase 4 feature)",
)
@click.option(
    "--batch",
    type=click.Path(exists=True, readable=True),
    help="Process multiple prompts from file (Phase 4 feature)",
)
@click.option(
    "--preset",
    type=click.Choice(["portrait", "landscape", "square", "hd", "artistic"]),
    help="Advanced parameter preset (Phase 4 feature)",
)
def image(
    prompt: str | None,
    size: str,
    quality: str,
    open_browser: bool,
    output_json: bool,
    output_path: str | None,
    no_enhance: bool,
    show_analytics: bool,
    variations: int | None,
    variation_strategy: str,
    no_cache: bool,
    cache_stats: bool,
    batch: str | None,
    preset: str | None,
) -> None:
    """
    Generate images from text prompts using gpt-image-1 with AI enhancements.

    Uses OpenAI's most advanced image generation model (gpt-image-1) with
    intelligent optimizations for superior results.

    Phase 2 Features:
    - Intelligent prompt enhancement for better results
    - Smart quality selection based on content analysis
    - Optimized parameter combinations for gpt-image-1
    - Research-backed improvements for artistic coherence

    Phase 3 Features:
    - Smart defaults based on prompt analysis
    - Session analytics and performance tracking
    - Enhanced error handling with helpful suggestions

    NEW Phase 4 Features:
    - Image variations with intelligent strategy selection
    - Multiple generation modes (creative, technical, style, mixed)
    - Batch processing for creative exploration
    - Advanced parameter combinations for power users

    Key advantages:
    - Auto-enhanced prompts for better quality and detail
    - Smart quality selection (analyzes complexity/content type)
    - Superior natural language understanding
    - Instant base64 image delivery (no delays)
    - Consistent results across similar prompts

    Images can be viewed in browser with --open or saved with --output.

    \b
    Examples:
        # Auto-enhanced generation (recommended)
        ei image "a mountain landscape at sunset"

        # Disable enhancement for precise control
        ei image "red circle on white background" --no-enhance

        # Smart quality selection for detailed work
        ei image "detailed portrait of an elderly craftsman" --quality auto

        # Save to specific file with landscape format
        ei image "wide panoramic cityscape" --size 1536x1024 -o city.png

        # Portrait format for tall subjects
        ei image "tall lighthouse on cliff" --size 1024x1536

    \b
    Advanced Tips:
        # Let gpt-image-1 choose optimal size and quality
        ei image "futuristic robot" --size auto --quality auto

        # Detailed prompt for better results
        ei image "photorealistic portrait of wise elderly wizard, \\
                  dramatic lighting, high contrast"

        # Style and mood descriptors work excellently
        ei image "cozy cabin in winter forest, warm lighting"

    \b
    Model: gpt-image-1 (OpenAI's most advanced image model)
        - Superior prompt understanding and artistic interpretation
        - Intelligent parameter selection with 'auto' settings
        - Consistent high-quality output with optimized generation pipeline
        - Fast base64 delivery eliminates URL expiration issues
    """
    # Check API key is configured
    require_api_key()

    console = Console()

    try:
        # Get AI service from factory
        factory = ServiceFactory()
        ai_service = factory.get_ai_service()

        # Validate input - need either prompt or batch file
        if not prompt and not batch:
            msg = "[red]Error: Must provide either PROMPT or --batch[/red]"
            console.print(msg)
            error_msg = "Missing argument 'PROMPT' or option '--batch'"
            raise click.UsageError(error_msg)
        
        # Apply preset if provided (Phase 4 advanced parameter combinations)
        if preset:
            size, quality = _apply_preset(preset, size, quality)
        
        # Display cache statistics if requested
        if cache_stats:
            stats = ai_service.get_cache_stats()
            console.print("\n[bold cyan]🗄️  Cache Statistics[/bold cyan]")
            console.print(f"Cache entries: {stats['entries']}")
            console.print(f"Cache hits: {stats['hits']}")
            console.print(f"Cache misses: {stats['misses']}")
            total_requests = stats["hits"] + stats["misses"]
            hit_rate = (
                stats["hits"] / total_requests * 100
                if total_requests > 0 else 0
            )
            console.print(f"Hit rate: {hit_rate:.1f}%")
            if not prompt and not batch:
                return None

        # Process batch file if provided
        if batch:
            return _process_batch_file(
                batch_file=batch,
                console=console,
                ai_service=ai_service,
                size=size,
                quality=quality,
                output_path=output_path,
                output_json=output_json,
                no_enhance=no_enhance,
                variations=variations,
                variation_strategy=variation_strategy,
                no_cache=no_cache,
            )

        # Check availability
        is_available, error = ai_service.check_available()
        if not is_available:  # pragma: no cover
            _handle_tool_unavailable(console, error)

        # Check if generating variations or single image
        if variations:
            # Generate multiple variations (Phase 4 feature)
            status_msg = f"[bold green]Generating {variations} variations..."
            if output_path:
                status_msg += " and saving..."

            with console.status(status_msg, spinner="dots"):
                variations_result = ai_service.generate_image_variations(
                    prompt=prompt,
                    count=variations,
                    size=size,
                    quality=quality,
                    output_dir=output_path,
                    show_progress=not output_json,
                    enhance_prompt=not no_enhance,
                    variation_strategy=variation_strategy,
                    use_cache=not no_cache,
                )

            # Display variations result
            if output_json:
                _display_variations_json_output(
                    console, variations_result, size, quality,
                )
            else:
                _display_variations_result(
                    console,
                    variations_result,
                    size,
                    quality,
                    open_browser,
                )
        else:
            # Generate single image using optimized gpt-image-1 pipeline
            status_msg = "[bold green]Generating image with gpt-image-1..."
            if output_path:
                status_msg += " and saving..."

            with console.status(status_msg, spinner="dots"):
                result = ai_service.generate_image(
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    output_path=output_path,
                    show_progress=not output_json,
                    enhance_prompt=not no_enhance,
                    use_cache=not no_cache,
                )

            # Display result
            if output_json:
                _display_json_output(console, result, size, quality)
            else:
                _display_result(
                    console,
                    result,
                    size,
                    quality,
                    open_browser,
                )

        # Show analytics summary if requested (Phase 3 feature)
        if show_analytics and not output_json:
            _display_analytics_summary(console, ai_service)

    except MissingAPIKeyError:
        console.print("[red]✗[/red] Missing API key: EI_API_KEY not set")
        console.print(
            "\n[yellow]Set your OpenAI API key:[/yellow]",
        )
        console.print("  export EI_API_KEY=your-key-here")
        raise Exit(1) from None
    except ServiceError as e:
        console.print(f"[red]✗[/red] {e}")
        raise Exit(1) from None
    except Exception as e:  # pragma: no cover
        console.print(f"[red]✗[/red] Unexpected error: {e}")
        raise Exit(1) from None
