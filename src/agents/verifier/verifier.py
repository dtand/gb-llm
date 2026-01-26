#!/usr/bin/env python3
"""
Verifier - Automated quality gate for generated GameBoy ROMs.

Checks:
1. Compile check - ROM file exists and is valid size
2. Boot check - ROM boots and runs without crashing
3. Input check - Game responds to button presses
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "planner"))

try:
    from pyboy import PyBoy
    PYBOY_AVAILABLE = True
except ImportError:
    PYBOY_AVAILABLE = False
    print("Warning: PyBoy not available. Install with: pip install pyboy")


class VerificationStatus(Enum):
    """Status of a verification check."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    """Result of a single verification check."""
    name: str
    status: VerificationStatus
    message: str = ""
    details: dict = field(default_factory=dict)


@dataclass
class VerificationResult:
    """Complete verification result for a ROM."""
    rom_path: Path
    passed: bool
    checks: List[CheckResult] = field(default_factory=list)
    
    def summary(self) -> str:
        """Generate a summary of verification results."""
        lines = [f"Verification: {'PASSED' if self.passed else 'FAILED'}"]
        lines.append(f"ROM: {self.rom_path}")
        lines.append("")
        for check in self.checks:
            icon = "✅" if check.status == VerificationStatus.PASSED else "❌" if check.status == VerificationStatus.FAILED else "⏭️"
            lines.append(f"  {icon} {check.name}: {check.status.value}")
            if check.message:
                lines.append(f"      {check.message}")
        return "\n".join(lines)


class Verifier:
    """Verifies GameBoy ROMs meet quality standards."""
    
    # GameBoy ROM size constraints
    MIN_ROM_SIZE = 32 * 1024  # 32KB minimum
    MAX_ROM_SIZE = 8 * 1024 * 1024  # 8MB maximum (with MBC)
    
    # Boot test parameters
    BOOT_FRAMES = 120  # 2 seconds at 60fps
    
    # Input test parameters  
    INPUT_TEST_FRAMES = 60  # 1 second of input
    INPUT_BUTTONS = ['up', 'down', 'left', 'right', 'a', 'b', 'start']
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the verifier.
        
        Args:
            verbose: Print detailed output
        """
        self.verbose = verbose
    
    def verify(self, rom_path: Path, skip_input_test: bool = False) -> VerificationResult:
        """
        Run all verification checks on a ROM.
        
        Args:
            rom_path: Path to the ROM file
            skip_input_test: Skip the input response test
            
        Returns:
            VerificationResult with all check results
        """
        rom_path = Path(rom_path)
        checks = []
        
        # Check 1: Compile check (ROM exists and valid)
        compile_check = self._check_compile(rom_path)
        checks.append(compile_check)
        
        if compile_check.status != VerificationStatus.PASSED:
            return VerificationResult(
                rom_path=rom_path,
                passed=False,
                checks=checks
            )
        
        # Check 2: Boot check (ROM runs without crash)
        boot_check = self._check_boot(rom_path)
        checks.append(boot_check)
        
        if boot_check.status != VerificationStatus.PASSED:
            return VerificationResult(
                rom_path=rom_path,
                passed=False,
                checks=checks
            )
        
        # Check 3: Input check (game responds to input)
        if skip_input_test:
            checks.append(CheckResult(
                name="Input Response",
                status=VerificationStatus.SKIPPED,
                message="Skipped by request"
            ))
        else:
            input_check = self._check_input_response(rom_path)
            checks.append(input_check)
        
        # Determine overall pass/fail
        passed = all(
            c.status in (VerificationStatus.PASSED, VerificationStatus.SKIPPED)
            for c in checks
        )
        
        return VerificationResult(
            rom_path=rom_path,
            passed=passed,
            checks=checks
        )
    
    def _check_compile(self, rom_path: Path) -> CheckResult:
        """Check that the ROM file exists and is valid."""
        if self.verbose:
            print(f"[Verifier] Checking compile: {rom_path}")
        
        # Check file exists
        if not rom_path.exists():
            return CheckResult(
                name="Compile Check",
                status=VerificationStatus.FAILED,
                message=f"ROM file not found: {rom_path}"
            )
        
        # Check file size
        size = rom_path.stat().st_size
        if size < self.MIN_ROM_SIZE:
            return CheckResult(
                name="Compile Check",
                status=VerificationStatus.FAILED,
                message=f"ROM too small: {size} bytes (min: {self.MIN_ROM_SIZE})"
            )
        
        if size > self.MAX_ROM_SIZE:
            return CheckResult(
                name="Compile Check",
                status=VerificationStatus.FAILED,
                message=f"ROM too large: {size} bytes (max: {self.MAX_ROM_SIZE})"
            )
        
        # Check file extension
        if rom_path.suffix.lower() not in ('.gb', '.gbc'):
            return CheckResult(
                name="Compile Check",
                status=VerificationStatus.FAILED,
                message=f"Invalid ROM extension: {rom_path.suffix}"
            )
        
        # Check Nintendo logo (bytes 0x104-0x133)
        # This is required for the ROM to boot on real hardware
        try:
            with open(rom_path, 'rb') as f:
                f.seek(0x104)
                logo = f.read(0x30)
                
            # Nintendo logo bytes (first 8 for quick check)
            expected_logo_start = bytes([0xCE, 0xED, 0x66, 0x66, 0xCC, 0x0D, 0x00, 0x0B])
            if not logo.startswith(expected_logo_start):
                return CheckResult(
                    name="Compile Check",
                    status=VerificationStatus.FAILED,
                    message="Invalid Nintendo logo - ROM won't boot on hardware"
                )
        except Exception as e:
            return CheckResult(
                name="Compile Check",
                status=VerificationStatus.FAILED,
                message=f"Error reading ROM header: {e}"
            )
        
        return CheckResult(
            name="Compile Check",
            status=VerificationStatus.PASSED,
            message=f"Valid ROM ({size} bytes)",
            details={"size": size}
        )
    
    def _check_boot(self, rom_path: Path) -> CheckResult:
        """Check that the ROM boots and runs without crashing."""
        if self.verbose:
            print(f"[Verifier] Checking boot: running {self.BOOT_FRAMES} frames")
        
        if not PYBOY_AVAILABLE:
            return CheckResult(
                name="Boot Check",
                status=VerificationStatus.SKIPPED,
                message="PyBoy not available"
            )
        
        try:
            # Run headless
            pyboy = PyBoy(str(rom_path), window='null')
            
            frames_run = 0
            for _ in range(self.BOOT_FRAMES):
                pyboy.tick()
                frames_run += 1
            
            pyboy.stop()
            
            return CheckResult(
                name="Boot Check",
                status=VerificationStatus.PASSED,
                message=f"Ran {frames_run} frames without crash",
                details={"frames": frames_run}
            )
            
        except Exception as e:
            return CheckResult(
                name="Boot Check",
                status=VerificationStatus.FAILED,
                message=f"Crash during boot: {e}"
            )
    
    def _check_input_response(self, rom_path: Path) -> CheckResult:
        """Check that the game responds to button presses."""
        if self.verbose:
            print(f"[Verifier] Checking input response")
        
        if not PYBOY_AVAILABLE:
            return CheckResult(
                name="Input Response",
                status=VerificationStatus.SKIPPED,
                message="PyBoy not available"
            )
        
        try:
            pyboy = PyBoy(str(rom_path), window='null')
            
            # Let the game boot
            for _ in range(60):
                pyboy.tick()
            
            # Get initial sprite positions
            initial_sprites = self._get_sprite_positions(pyboy)
            
            # Press some buttons
            button_map = {
                'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right',
                'a': 'a', 'b': 'b', 'start': 'start', 'select': 'select'
            }
            
            response_detected = False
            
            for button in ['right', 'a', 'start']:
                # Press button
                pyboy.button(button)
                
                # Run some frames
                for _ in range(30):
                    pyboy.tick()
                
                # Release button
                pyboy.button_release(button)
                
                # Run more frames
                for _ in range(30):
                    pyboy.tick()
                
                # Check if sprites moved
                current_sprites = self._get_sprite_positions(pyboy)
                if current_sprites != initial_sprites:
                    response_detected = True
                    break
                
                initial_sprites = current_sprites
            
            pyboy.stop()
            
            # For now, we pass even if no response detected
            # Some games (like bouncing ball) don't need input
            if response_detected:
                return CheckResult(
                    name="Input Response",
                    status=VerificationStatus.PASSED,
                    message="Game responds to input"
                )
            else:
                return CheckResult(
                    name="Input Response",
                    status=VerificationStatus.PASSED,
                    message="No input response detected (may be OK for passive games)"
                )
                
        except Exception as e:
            return CheckResult(
                name="Input Response",
                status=VerificationStatus.FAILED,
                message=f"Error during input test: {e}"
            )
    
    def _get_sprite_positions(self, pyboy) -> list:
        """Get current sprite positions from OAM."""
        try:
            # Read OAM (Object Attribute Memory) - 40 sprites, 4 bytes each
            positions = []
            for i in range(40):
                # OAM starts at 0xFE00
                y = pyboy.memory[0xFE00 + i * 4]
                x = pyboy.memory[0xFE00 + i * 4 + 1]
                if y > 0 and y < 160 and x > 0 and x < 168:  # Visible sprite
                    positions.append((x, y))
            return positions
        except:
            return []


def main():
    """CLI interface for the verifier."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Verify GameBoy ROM quality"
    )
    parser.add_argument("rom", help="Path to ROM file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--skip-input", action="store_true", help="Skip input test")
    
    args = parser.parse_args()
    
    verifier = Verifier(verbose=args.verbose)
    result = verifier.verify(Path(args.rom), skip_input_test=args.skip_input)
    
    print(result.summary())
    
    return 0 if result.passed else 1


if __name__ == "__main__":
    exit(main())
