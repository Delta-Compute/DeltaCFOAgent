import type { Config } from "jest";
import nextJest from "next/jest";

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files
  dir: "./",
});

const config: Config = {
  // Indicates whether the coverage information should be collected while executing the test
  collectCoverage: true,

  // The directory where Jest should output its coverage files
  coverageDirectory: "coverage",

  // An array of glob patterns indicating a set of files for which coverage information should be collected
  collectCoverageFrom: [
    "src/**/*.{js,jsx,ts,tsx}",
    "!src/**/*.d.ts",
    "!src/**/*.stories.{js,jsx,ts,tsx}",
    "!src/app/**/layout.tsx",
    "!src/app/**/loading.tsx",
    "!src/app/**/error.tsx",
    "!src/app/**/not-found.tsx",
  ],

  // The test environment that will be used for testing
  testEnvironment: "jsdom",

  // Setup files to run after Jest is initialized
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],

  // A map from regular expressions to module names or to arrays of module names
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
  },

  // An array of regexp pattern strings that are matched against all test paths
  testPathIgnorePatterns: ["<rootDir>/node_modules/", "<rootDir>/.next/"],

  // An array of regexp pattern strings that are matched against all source file paths
  transformIgnorePatterns: [
    "/node_modules/",
    "^.+\\.module\\.(css|sass|scss)$",
  ],

  // Indicates whether each individual test should be reported during the run
  verbose: true,
};

export default createJestConfig(config);
