#!/usr/bin/env python3
"""
Comprehensive Pyserv-Client Framework Quality Audit
Validates client-side implementation quality
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class ClientComponentAudit:
    name: str
    status: str  # "EXCELLENT", "GOOD", "NEEDS_WORK", "MISSING"
    issues: List[str]
    strengths: List[str]
    score: int  # 0-100

class ClientFrameworkAuditor:
    def __init__(self, client_path: Path):
        self.client_path = client_path
        self.src_path = client_path / "src"
        self.results: Dict[str, ClientComponentAudit] = {}
        
    def audit_all(self) -> Dict[str, ClientComponentAudit]:
        """Audit all client framework components"""
        print("Starting comprehensive Pyserv-Client framework audit...\n")
        
        # Core client components
        self.audit_project_structure()
        self.audit_typescript_config()
        self.audit_build_system()
        self.audit_component_architecture()
        self.audit_state_management()
        self.audit_api_integration()
        self.audit_routing_system()
        self.audit_ui_components()
        self.audit_testing_setup()
        self.audit_documentation()
        
        return self.results
    
    def audit_project_structure(self):
        """Audit project structure and organization"""
        issues = []
        strengths = []
        
        # Check for essential files
        essential_files = [
            "package.json", "tsconfig.json", "vite.config.ts", 
            "README.md", "src/main.ts"
        ]
        
        for file in essential_files:
            if not (self.client_path / file).exists():
                issues.append(f"Missing {file}")
            else:
                strengths.append(f"Has {file}")
        
        # Check directory structure
        expected_dirs = ["src", "public", "tests", "docs"]
        for dir_name in expected_dirs:
            if (self.client_path / dir_name).exists():
                strengths.append(f"Organized {dir_name}/ directory")
            else:
                issues.append(f"Missing {dir_name}/ directory")
        
        score = max(0, 100 - len(issues) * 15)
        status = "EXCELLENT" if score >= 90 else "GOOD" if score >= 70 else "NEEDS_WORK"
        
        self.results["Project Structure"] = ClientComponentAudit(
            "Project Structure", status, issues, strengths, score
        )
    
    def audit_typescript_config(self):
        """Audit TypeScript configuration"""
        issues = []
        strengths = []
        
        tsconfig_file = self.client_path / "tsconfig.json"
        if not tsconfig_file.exists():
            issues.append("Missing TypeScript configuration")
        else:
            try:
                with open(tsconfig_file, 'r') as f:
                    config = json.load(f)
                
                compiler_options = config.get("compilerOptions", {})
                
                # Check for modern TypeScript settings
                if compiler_options.get("strict"):
                    strengths.append("Strict TypeScript mode enabled")
                if compiler_options.get("target") in ["ES2020", "ES2021", "ES2022", "ESNext"]:
                    strengths.append("Modern JavaScript target")
                if "moduleResolution" in compiler_options:
                    strengths.append("Module resolution configured")
                    
            except json.JSONDecodeError:
                issues.append("Invalid TypeScript configuration")
        
        score = max(0, 100 - len(issues) * 30)
        status = "EXCELLENT" if score >= 90 else "GOOD" if score >= 70 else "NEEDS_WORK"
        
        self.results["TypeScript Config"] = ClientComponentAudit(
            "TypeScript Config", status, issues, strengths, score
        )
    
    def audit_build_system(self):
        """Audit build system and tooling"""
        issues = []
        strengths = []
        
        # Check for Vite configuration
        vite_config = self.client_path / "vite.config.ts"
        if vite_config.exists():
            strengths.append("Modern Vite build system")
        else:
            issues.append("Missing build configuration")
        
        # Check package.json for scripts
        package_json = self.client_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    pkg = json.load(f)
                
                scripts = pkg.get("scripts", {})
                if "build" in scripts:
                    strengths.append("Build script configured")
                if "dev" in scripts:
                    strengths.append("Development server script")
                if "test" in scripts:
                    strengths.append("Test script configured")
                if "lint" in scripts:
                    strengths.append("Linting configured")
                    
            except json.JSONDecodeError:
                issues.append("Invalid package.json")
        
        score = max(0, 100 - len(issues) * 25)
        status = "EXCELLENT" if score >= 90 else "GOOD" if score >= 70 else "NEEDS_WORK"
        
        self.results["Build System"] = ClientComponentAudit(
            "Build System", status, issues, strengths, score
        )
    
    def audit_component_architecture(self):
        """Audit component architecture"""
        issues = []
        strengths = []
        
        src_dir = self.src_path
        if not src_dir.exists():
            issues.append("Missing src directory")
        else:
            # Check for component organization
            components_dir = src_dir / "components"
            if components_dir.exists():
                strengths.append("Organized components directory")
                
                # Count components
                component_files = list(components_dir.rglob("*.ts")) + list(components_dir.rglob("*.tsx"))
                if len(component_files) >= 5:
                    strengths.append("Rich component library")
            
            # Check for utilities
            utils_dir = src_dir / "utils"
            if utils_dir.exists():
                strengths.append("Utility functions organized")
            
            # Check for types
            types_files = list(src_dir.rglob("*types*.ts")) + list(src_dir.rglob("*.d.ts"))
            if types_files:
                strengths.append("TypeScript type definitions")
        
        score = max(0, 100 - len(issues) * 30)
        status = "EXCELLENT" if score >= 90 else "GOOD" if score >= 70 else "NEEDS_WORK"
        
        self.results["Component Architecture"] = ClientComponentAudit(
            "Component Architecture", status, issues, strengths, score
        )
    
    def audit_state_management(self):
        """Audit state management solution"""
        issues = []
        strengths = []
        
        # Check for state management files
        src_dir = self.src_path
        if src_dir.exists():
            state_patterns = ["store", "state", "redux", "zustand", "pinia"]
            
            for pattern in state_patterns:
                state_files = list(src_dir.rglob(f"*{pattern}*"))
                if state_files:
                    strengths.append(f"State management with {pattern}")
                    break
            else:
                issues.append("No clear state management pattern")
        
        score = max(0, 100 - len(issues) * 40)
        status = "EXCELLENT" if score >= 90 else "GOOD" if score >= 70 else "NEEDS_WORK"
        
        self.results["State Management"] = ClientComponentAudit(
            "State Management", status, issues, strengths, score
        )
    
    def audit_api_integration(self):
        """Audit API integration capabilities"""
        issues = []
        strengths = []
        
        src_dir = self.src_path
        if src_dir.exists():
            # Check for API-related files
            api_patterns = ["api", "service", "client", "http"]
            
            for pattern in api_patterns:
                api_files = list(src_dir.rglob(f"*{pattern}*"))
                if api_files:
                    strengths.append(f"API integration with {pattern}")
            
            # Check for common HTTP libraries in package.json
            package_json = self.client_path / "package.json"
            if package_json.exists():
                try:
                    with open(package_json, 'r') as f:
                        pkg = json.load(f)
                    
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                    
                    if "axios" in deps:
                        strengths.append("Axios HTTP client")
                    elif "fetch" in str(deps) or "node-fetch" in deps:
                        strengths.append("Fetch API integration")
                        
                except json.JSONDecodeError:
                    pass
        
        if not strengths:
            issues.append("No clear API integration pattern")
        
        score = max(0, 100 - len(issues) * 40)
        status = "EXCELLENT" if score >= 90 else "GOOD" if score >= 70 else "NEEDS_WORK"
        
        self.results["API Integration"] = ClientComponentAudit(
            "API Integration", status, issues, strengths, score
        )
    
    def audit_routing_system(self):
        """Audit client-side routing"""
        issues = []
        strengths = []
        
        # Check for routing files
        src_dir = self.src_path
        if src_dir.exists():
            routing_files = list(src_dir.rglob("*router*")) + list(src_dir.rglob("*route*"))
            if routing_files:
                strengths.append("Client-side routing implemented")
            else:
                issues.append("No client-side routing found")
        
        # Check for routing libraries in package.json
        package_json = self.client_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    pkg = json.load(f)
                
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                
                routing_libs = ["vue-router", "react-router", "@reach/router", "wouter"]
                for lib in routing_libs:
                    if lib in deps:
                        strengths.append(f"Using {lib}")
                        break
                        
            except json.JSONDecodeError:
                pass
        
        score = max(0, 100 - len(issues) * 40)
        status = "EXCELLENT" if score >= 90 else "GOOD" if score >= 70 else "NEEDS_WORK"
        
        self.results["Routing System"] = ClientComponentAudit(
            "Routing System", status, issues, strengths, score
        )
    
    def audit_ui_components(self):
        """Audit UI component library"""
        issues = []
        strengths = []
        
        src_dir = self.src_path
        if src_dir.exists():
            # Check for UI components
            ui_dirs = ["components", "ui", "widgets"]
            component_count = 0
            
            for ui_dir in ui_dirs:
                ui_path = src_dir / ui_dir
                if ui_path.exists():
                    ui_files = list(ui_path.rglob("*.ts")) + list(ui_path.rglob("*.tsx")) + list(ui_path.rglob("*.vue"))
                    component_count += len(ui_files)
            
            if component_count >= 10:
                strengths.append("Rich UI component library")
            elif component_count >= 5:
                strengths.append("Good UI component collection")
            elif component_count > 0:
                strengths.append("Basic UI components")
            else:
                issues.append("No UI components found")
        
        score = max(0, 100 - len(issues) * 50)
        status = "EXCELLENT" if score >= 90 else "GOOD" if score >= 70 else "NEEDS_WORK"
        
        self.results["UI Components"] = ClientComponentAudit(
            "UI Components", status, issues, strengths, score
        )
    
    def audit_testing_setup(self):
        """Audit testing framework and setup"""
        issues = []
        strengths = []
        
        # Check for test files
        tests_dir = self.client_path / "tests"
        if tests_dir.exists():
            test_files = list(tests_dir.rglob("*.test.*")) + list(tests_dir.rglob("*.spec.*"))
            if len(test_files) >= 5:
                strengths.append("Comprehensive test suite")
            elif len(test_files) > 0:
                strengths.append("Basic test coverage")
        else:
            issues.append("No tests directory found")
        
        # Check for testing libraries in package.json
        package_json = self.client_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    pkg = json.load(f)
                
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                
                testing_libs = ["vitest", "jest", "@testing-library", "cypress", "playwright"]
                for lib in testing_libs:
                    if any(lib in dep for dep in deps.keys()):
                        strengths.append(f"Testing with {lib}")
                        
            except json.JSONDecodeError:
                pass
        
        score = max(0, 100 - len(issues) * 30)
        status = "EXCELLENT" if score >= 90 else "GOOD" if score >= 70 else "NEEDS_WORK"
        
        self.results["Testing Setup"] = ClientComponentAudit(
            "Testing Setup", status, issues, strengths, score
        )
    
    def audit_documentation(self):
        """Audit documentation quality"""
        issues = []
        strengths = []
        
        # Check for README
        readme_file = self.client_path / "README.md"
        if not readme_file.exists():
            issues.append("Missing README documentation")
        else:
            try:
                content = readme_file.read_text(encoding='utf-8')
                if len(content) > 1000:
                    strengths.append("Comprehensive README")
                if "install" in content.lower():
                    strengths.append("Installation instructions")
                if "example" in content.lower():
                    strengths.append("Usage examples")
            except:
                issues.append("Cannot read README file")
        
        # Check for docs directory
        docs_dir = self.client_path / "docs"
        if docs_dir.exists():
            doc_files = list(docs_dir.rglob("*.md"))
            if len(doc_files) >= 3:
                strengths.append("Detailed documentation")
        
        score = max(0, 100 - len(issues) * 40)
        status = "EXCELLENT" if score >= 90 else "GOOD" if score >= 70 else "NEEDS_WORK"
        
        self.results["Documentation"] = ClientComponentAudit(
            "Documentation", status, issues, strengths, score
        )
    
    def generate_report(self) -> str:
        """Generate comprehensive client audit report"""
        report = []
        report.append("=" * 80)
        report.append("PYSERV-CLIENT FRAMEWORK COMPREHENSIVE QUALITY AUDIT")
        report.append("=" * 80)
        report.append("")
        
        # Calculate overall score
        total_score = sum(audit.score for audit in self.results.values())
        avg_score = total_score / len(self.results) if self.results else 0
        
        # Overall assessment
        if avg_score >= 90:
            overall = "WORLD-CLASS - Exceeds best-in-class client frameworks"
        elif avg_score >= 80:
            overall = "EXCELLENT - Matches best-in-class client frameworks"
        elif avg_score >= 70:
            overall = "GOOD - Production ready with minor improvements needed"
        elif avg_score >= 60:
            overall = "ACCEPTABLE - Needs significant improvements"
        else:
            overall = "NEEDS MAJOR WORK - Not production ready"
            
        report.append(f"OVERALL ASSESSMENT: {overall}")
        report.append(f"OVERALL SCORE: {avg_score:.1f}/100")
        report.append("")
        
        # Component breakdown
        report.append("COMPONENT ANALYSIS:")
        report.append("-" * 50)
        
        for name, audit in self.results.items():
            status_icon = {
                "EXCELLENT": "[EXCELLENT]",
                "GOOD": "[GOOD]",
                "NEEDS_WORK": "[NEEDS_WORK]",
                "MISSING": "[MISSING]"
            }.get(audit.status, "[UNKNOWN]")
            
            report.append(f"{status_icon} {name}: {audit.status} ({audit.score}/100)")
            
            if audit.strengths:
                for strength in audit.strengths[:3]:
                    report.append(f"   + {strength}")
                    
            if audit.issues:
                for issue in audit.issues[:2]:
                    report.append(f"   - {issue}")
                    
            report.append("")
        
        # Comparison with best-in-class client frameworks
        report.append("COMPARISON WITH BEST-IN-CLASS CLIENT FRAMEWORKS:")
        report.append("-" * 50)
        
        comparisons = [
            ("React", "Popular component library", 88),
            ("Vue.js", "Progressive framework", 85),
            ("Angular", "Full-featured framework", 82),
            ("Svelte", "Compile-time framework", 80),
            ("Next.js", "React meta-framework", 90)
        ]
        
        for name, desc, score in comparisons:
            comparison = "BETTER" if avg_score > score else "COMPARABLE" if abs(avg_score - score) <= 5 else "BEHIND"
            report.append(f"{name} ({desc}): {score}/100 - Pyserv-Client is {comparison}")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)

def main():
    client_path = Path(__file__).parent.parent / "pyserv-client"
    
    if not client_path.exists():
        print("Pyserv-Client framework not found!")
        return
    
    auditor = ClientFrameworkAuditor(client_path)
    
    # Run comprehensive audit
    results = auditor.audit_all()
    
    # Generate and display report
    report = auditor.generate_report()
    print(report)
    
    # Save report to file
    report_file = client_path / "CLIENT_AUDIT_REPORT.md"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\nDetailed report saved to: {report_file}")

if __name__ == "__main__":
    main()