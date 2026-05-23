import re

class AIGrading:
    @staticmethod
    def grade_code_submission(code_content, requirements):
        """Grade programming/code submissions"""
        score = 0
        feedback = []
        breakdown = {}
        
        if not code_content:
            return 0, ["No code content to analyze."], {}
        
        # Check structure (functions/classes)
        has_functions = len(re.findall(r"def\s+\w+\s*\(", code_content)) > 0
        has_classes = len(re.findall(r"class\s+\w+", code_content)) > 0
        
        if has_functions or has_classes:
            score += 25
            feedback.append("✅ Good code organization with functions/classes")
            breakdown["Structure"] = 25
        else:
            feedback.append("⚠️ Consider using functions to organize your code")
            breakdown["Structure"] = 0
        
        # Check comments/documentation
        comment_lines = len(re.findall(r"#.*$", code_content, re.MULTILINE))
        if comment_lines > 5:
            score += 20
            feedback.append("✅ Well documented with comments")
            breakdown["Documentation"] = 20
        elif comment_lines > 2:
            score += 10
            feedback.append("✓ Has some comments, consider adding more")
            breakdown["Documentation"] = 10
        else:
            feedback.append("⚠️ Add comments to explain your code")
            breakdown["Documentation"] = 0
        
        # Check naming conventions
        has_good_naming = len(re.findall(r"[a-z]+_[a-z]+", code_content)) > 3
        if has_good_naming:
            score += 15
            feedback.append("✅ Good variable naming convention")
            breakdown["Naming"] = 15
        else:
            breakdown["Naming"] = 0
        
        # Check error handling
        if "try:" in code_content and "except" in code_content:
            score += 20
            feedback.append("✅ Good error handling with try-except")
            breakdown["Error Handling"] = 20
        else:
            feedback.append("💡 Consider adding error handling")
            breakdown["Error Handling"] = 0
        
        # Code length/completeness
        lines = code_content.split('\n')
        if len(lines) > 10:
            score += 20
            feedback.append("✓ Appropriate code length")
            breakdown["Completeness"] = 20
        else:
            feedback.append("⚠️ Code is quite short, consider adding more implementation")
            breakdown["Completeness"] = 10
        
        return min(score, 100), feedback, breakdown
    
    @staticmethod
    def grade_theory_submission(content, keywords):
        """Grade theory/essay submissions"""
        score = 0
        feedback = []
        breakdown = {}
        
        if not content:
            return 0, ["No content to analyze."], {}
        
        # Check length/word count
        word_count = len(content.split())
        
        if word_count >= 500:
            score += 30
            feedback.append("✅ Comprehensive answer with good length")
            breakdown["Length"] = 30
        elif word_count >= 300:
            score += 20
            feedback.append("✓ Good length, could add more detail")
            breakdown["Length"] = 20
        elif word_count >= 150:
            score += 10
            feedback.append("⚠️ Answer is brief, expand your explanation")
            breakdown["Length"] = 10
        else:
            feedback.append("❌ Answer is too short")
            breakdown["Length"] = 0
        
        # Keyword matching
        content_lower = content.lower()
        matched_keywords = []
        
        for kw in keywords[:10]:  # Limit to first 10 keywords
            if kw.lower() in content_lower:
                matched_keywords.append(kw)
        
        keyword_score = (len(matched_keywords) / max(len(keywords[:10]), 1)) * 40
        score += keyword_score
        
        if keyword_score >= 30:
            feedback.append(f"✅ Covered {len(matched_keywords)} key concepts")
        elif keyword_score >= 20:
            feedback.append(f"✓ Covered some key concepts")
        else:
            feedback.append("⚠️ Missing important key concepts")
        
        breakdown["Keywords"] = round(keyword_score, 1)
        
        # Check for examples
        if "example" in content_lower or "for instance" in content_lower:
            score += 15
            feedback.append("✅ Good use of examples")
            breakdown["Examples"] = 15
        else:
            feedback.append("💡 Add examples to strengthen your answer")
            breakdown["Examples"] = 0
        
        # Check structure (paragraphs)
        paragraphs = content.split('\n\n')
        if len(paragraphs) >= 3:
            score += 15
            feedback.append("✓ Well-structured with multiple paragraphs")
            breakdown["Structure"] = 15
        elif len(paragraphs) >= 2:
            score += 10
            feedback.append("✓ Has some structure")
            breakdown["Structure"] = 10
        else:
            breakdown["Structure"] = 5
        
        return min(score, 100), feedback, breakdown
    
    @staticmethod
    def get_improvement_suggestions(score, feedback):
        """Generate personalized improvement suggestions"""
        suggestions = []
        
        if score < 50:
            suggestions.append("📚 Review the course materials thoroughly")
            suggestions.append("✍️ Provide more detailed explanations")
            suggestions.append("💡 Add practical examples to support your points")
        elif score < 70:
            suggestions.append("🎯 Focus on key concepts highlighted in the feedback")
            suggestions.append("📝 Structure your answer with clear sections")
            suggestions.append("🔍 Proofread and check for completeness")
        else:
            suggestions.append("🌟 Excellent work! Keep up the good practices")
            suggestions.append("🚀 Challenge yourself with advanced concepts")
        
        # Add specific feedback-based suggestions
        for fb in feedback:
            if "short" in fb.lower():
                suggestions.append("📖 Expand your answer with more details")
            if "keywords" in fb.lower() and "missing" in fb.lower():
                suggestions.append("📋 List and explain key terms before writing")
            if "examples" in fb.lower():
                suggestions.append("💡 Use real-world examples to illustrate points")
        
        return suggestions[:5]